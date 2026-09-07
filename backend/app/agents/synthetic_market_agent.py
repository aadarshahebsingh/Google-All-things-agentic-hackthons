"""Synthetic Market Agent — persona population, multi-round simulation,
scenario engine (independent stream B). All outputs labeled SIMULATED."""
from __future__ import annotations

import statistics

from ..services import simulation_service as sim
from ..services.event_service import log_event
from ..services.firestore_service import get_firestore_service


def run_synthetic_market_agent(startup_id: str, startup: dict, research_result: dict | None = None) -> dict:
    fs = get_firestore_service()
    log_event(startup_id, "SyntheticMarketAgent", "Generating market population model")

    population = sim.default_population_model()
    # Ground the population in research when available.
    if research_result and research_result.get("evidence_count", 0) > 10:
        population.pain_severity_distribution = {"low": 0.15, "medium": 0.45, "high": 0.40}
        population.ai_trust_distribution = {"low": 0.30, "medium": 0.50, "high": 0.20}
    fs.set("personas_meta", startup_id, {"population_model": population.model_dump(),
                                         "grounded_in_research": bool(research_result)})

    log_event(startup_id, "SyntheticMarketAgent", "Generating 10,000 synthetic personas")
    personas = sim.generate_personas(startup_id, population, count=10000)

    product = startup.get("solution", "the product")[:80]
    products = [product, f"{product} (lite)", f"{product} (pro)"]
    prices = [0.0, 49.0, 99.0, 199.0, 499.0]
    positionings = ["save time", "AI co-pilot", "cheaper alternative"]

    # Multi-round behavioral simulation with influence propagation.
    reactions_by_round = []
    for rnd in range(1, 6):
        influence = 0.0 if rnd == 1 else min(0.35, 0.08 * rnd)
        reactions = sim.run_simulation_round(personas, product, 99.0, "save time", rnd, influence)
        reactions_by_round.append(reactions)
        log_event(startup_id, "PersonaSimulation", f"Round {rnd}/5 complete ({len(reactions)} participants)")

    final_reactions = reactions_by_round[-1]
    seg_summary = sim.segment_summary(final_reactions)
    log_event(startup_id, "SyntheticMarketAgent",
              f"Best segment: {next(iter(seg_summary), 'n/a')}")

    log_event(startup_id, "ScenarioEngine", "Testing product x price x positioning scenarios")
    scenarios = sim.run_scenario_grid(personas[:2000], products, prices, positionings)
    best_seg = next(iter(seg_summary), None)
    focused = sim.run_scenario_grid(
        [p for p in personas if p.segment == best_seg][:2000] if best_seg else personas[:2000],
        products, prices, positionings, segments=None)
    all_scenarios = sorted(scenarios + focused, key=lambda s: s.score, reverse=True)

    scores = sim.synthetic_market_score(final_reactions, all_scenarios)
    result = {
        "participant_count": len(personas),
        "segments": seg_summary,
        "scenario_scores": [s.model_dump() for s in all_scenarios[:8]],
        "scores": scores,
        "round_summaries": [
            {"round": i + 1, "mean_interest": round(statistics.mean(r.interest for r in rs), 3)}
            for i, rs in enumerate(reactions_by_round)
        ],
        "objections": _top_objections(final_reactions),
    }
    fs.set("simulations", startup_id, {"startup_id": startup_id, **result})
    log_event(startup_id, "SyntheticMarketAgent",
              f"Synthetic Market Score: {scores['synthetic_market_score']} (SIMULATED)")
    return result


def _top_objections(reactions) -> list[str]:
    counts: dict[str, int] = {}
    for r in reactions:
        for o in r.main_objections:
            counts[o] = counts.get(o, 0) + 1
    return sorted(counts, key=counts.get, reverse=True)[:5]
