"""Unit tests: persona generation, simulation, market fit, conflicts, calendar dedup."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.persona import Persona  # noqa: E402
from app.services import simulation_service as sim  # noqa: E402
from app.services.market_fit_service import compute_market_fit, detect_conflicts  # noqa: E402


def test_persona_generation_deterministic():
    pop = sim.default_population_model()
    p1 = sim.generate_personas("s1", pop, count=100, seed=42)
    p2 = sim.generate_personas("s1", pop, count=100, seed=42)
    assert len(p1) == 100
    assert [x.ai_trust for x in p1] == [x.ai_trust for x in p2]


def test_persona_segments_assigned():
    pop = sim.default_population_model()
    personas = sim.generate_personas("s1", pop, count=500)
    segments = {p.segment for p in personas}
    assert "general" in segments or len(segments) > 1


def test_simulation_reaction_bounds():
    persona = Persona(persona_id="p1", startup_id="s1", pain_severity=0.9,
                      ai_trust=0.8, price_sensitivity=0.2, budget_monthly=500,
                      current_solution="manual")
    r = sim.simulate_reaction(persona, "product", 99.0, "save time")
    for v in (r.interest, r.trust, r.willingness_to_pay):
        assert 0.0 <= v <= 1.0


def test_price_reduces_willingness():
    persona = Persona(persona_id="p1", startup_id="s1", pain_severity=0.5,
                      ai_trust=0.5, price_sensitivity=0.9, budget_monthly=100,
                      current_solution="manual")
    cheap = sim.simulate_reaction(persona, "p", 49.0, "save time")
    expensive = sim.simulate_reaction(persona, "p", 499.0, "save time")
    assert cheap.willingness_to_pay >= expensive.willingness_to_pay


def test_scenario_grid_sorted():
    pop = sim.default_population_model()
    personas = sim.generate_personas("s1", pop, count=200)
    results = sim.run_scenario_grid(personas, ["A", "B"], [49.0, 199.0], ["save time"])
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_synthetic_score_labeled_simulated():
    pop = sim.default_population_model()
    personas = sim.generate_personas("s1", pop, count=50)
    reactions = sim.run_simulation_round(personas, "p", 99.0, "save time", 1)
    result = sim.synthetic_market_score(reactions, [])
    assert result["label"] == "SIMULATED"


def test_market_fit_without_real_customers_lower_confidence():
    synthetic = {"scores": {"synthetic_market_score": 79, "synthetic_demand_score": 80,
                            "synthetic_trust_score": 60, "synthetic_pricing_score": 55,
                            "synthetic_adoption_score": 70, "synthetic_switching_score": 63}}
    no_real = compute_market_fit("s1", None, {"scores": synthetic["scores"]}, None, [])
    with_real = compute_market_fit("s1", {"research_score": 82}, {"scores": synthetic["scores"]},
                                   {"candidates_found": 15, "responses": 11, "mean_relevance": 85},
                                   [{"problem_confirmed": True, "pain_score": 8, "interest_score": 8,
                                     "trust_score": 6, "dimension_hints": {}}])
    assert with_real.confidence > no_real.confidence


def test_conflict_detection():
    dims = []
    from app.models.market_fit import DimensionScore

    d = DimensionScore(dimension="pricing")
    d.research_evidence = {"score": 85.0, "present": True}
    d.customer_evidence = {"score": 40.0, "present": True}
    d.synthetic_evidence = {"score": 70.0, "present": True}
    d.voice_evidence = {"present": False}
    conflicts = detect_conflicts("s1", [d], [])
    assert len(conflicts) == 1
    assert set(conflicts[0].sources_disagreeing) == {"research", "customer", "synthetic"}


def test_no_conflict_when_streams_agree():
    from app.models.market_fit import DimensionScore

    d = DimensionScore(dimension="demand")
    d.research_evidence = {"score": 80.0, "present": True}
    d.synthetic_evidence = {"score": 78.0, "present": True}
    d.voice_evidence = {"present": False}
    d.customer_evidence = {"present": False}
    assert detect_conflicts("s1", [d], []) == []


def test_calendar_event_fingerprint_stable():
    from app.tools.calendar_tools import _event_fingerprint

    a = _event_fingerprint("s1", "Prep deck", "2026-09-07")
    b = _event_fingerprint("s1", "Prep deck", "2026-09-07")
    c = _event_fingerprint("s1", "Prep deck", "2026-09-08")
    assert a == b and a != c


def test_outreach_rate_limit():
    from app.tools.email_tools import check_rate_limit

    results = [check_rate_limit() for _ in range(10)]
    assert results.count(True) <= 5
