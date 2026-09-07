"""Deterministic synthetic market simulation engine.

Personas are generated from a researched population model using seeded RNG.
This is a SCENARIO SIMULATION grounded in research — never presented as real
market demand.
"""
from __future__ import annotations

import random
import statistics
import uuid
from collections import defaultdict

from ..models.persona import (
    Persona,
    PersonaReaction,
    PopulationModel,
    ScenarioResult,
)

SEGMENT_RULES = [
    ("early_adopters", lambda p: p.technology_adoption > 0.7 and p.risk_tolerance > 0.6),
    ("ai_enthusiasts", lambda p: p.ai_trust > 0.7),
    ("skeptics", lambda p: p.ai_trust < 0.35),
    ("price_sensitive", lambda p: p.price_sensitivity > 0.7),
    ("premium", lambda p: p.price_sensitivity < 0.3 and p.budget_monthly > 300),
    ("severe_pain", lambda p: p.pain_severity > 0.75),
    ("low_pain", lambda p: p.pain_severity < 0.3),
    ("general", lambda p: True),
]


def default_population_model() -> PopulationModel:
    """Baseline distributions; the research agent refines these from evidence."""
    return PopulationModel(
        age_distribution={"18-24": 0.35, "25-34": 0.35, "35-44": 0.2, "45+": 0.1},
        location_distribution={"urban": 0.5, "suburban": 0.35, "rural": 0.15},
        income_distribution={"low": 0.4, "middle": 0.45, "high": 0.15},
        experience_distribution={"student": 0.3, "early_career": 0.35, "mid": 0.25, "senior": 0.1},
        ai_trust_distribution={"low": 0.25, "medium": 0.5, "high": 0.25},
        price_sensitivity_distribution={"low": 0.3, "medium": 0.45, "high": 0.25},
        current_solution_distribution={"manual": 0.5, "competitor_a": 0.25, "competitor_b": 0.15, "none": 0.1},
        pain_severity_distribution={"low": 0.2, "medium": 0.5, "high": 0.3},
    )


def _pick(rng: random.Random, dist: dict[str, float]) -> str:
    r = rng.random()
    acc = 0.0
    for k, v in dist.items():
        acc += v
        if r <= acc:
            return k
    return next(iter(dist), "unknown")


def generate_personas(startup_id: str, population: PopulationModel, count: int = 10000, seed: int = 42) -> list[Persona]:
    """Generate personas by sampling the population distributions."""
    rng = random.Random(seed)
    personas: list[Persona] = []
    for i in range(count):
        age = _pick(rng, population.age_distribution)
        income = _pick(rng, population.income_distribution)
        exp = _pick(rng, population.experience_distribution)
        trust_bucket = _pick(rng, population.ai_trust_distribution)
        psens_bucket = _pick(rng, population.price_sensitivity_distribution)
        pain_bucket = _pick(rng, population.pain_severity_distribution)
        solution = _pick(rng, population.current_solution_distribution)

        base = {"low": 0.2, "medium": 0.5, "high": 0.8}
        budget = {"low": 50.0, "middle": 200.0, "high": 600.0}

        persona = Persona(
            persona_id=f"{startup_id}-p{i:05d}",
            startup_id=startup_id,
            demographics={"age_band": age, "income_band": income, "location": _pick(rng, population.location_distribution)},
            occupation=exp,
            budget_monthly=budget.get(income, 150.0),
            ai_trust=max(0.0, min(1.0, rng.gauss(base[trust_bucket], 0.12))),
            price_sensitivity=max(0.0, min(1.0, rng.gauss(base[psens_bucket], 0.12))),
            risk_tolerance=rng.random(),
            technology_adoption=rng.random(),
            automation_preference=rng.random(),
            pain_severity=max(0.0, min(1.0, rng.gauss(base[pain_bucket], 0.15))),
            willingness_to_pay=0.0,
            current_solution=solution,
            goals=["solve the core problem faster"],
            pain_points=["current process is slow and manual"],
            beliefs=[f"trusts AI: {trust_bucket}", f"price sensitivity: {psens_bucket}"],
        )
        persona.willingness_to_pay = max(0.0, min(1.0, persona.pain_severity * 0.6 + (1 - persona.price_sensitivity) * 0.4))
        for seg_name, rule in SEGMENT_RULES:
            if rule(persona):
                persona.segment = seg_name
                break
        personas.append(persona)
    return personas


def simulate_reaction(persona: Persona, product: str, price: float, positioning: str, round_num: int = 1) -> PersonaReaction:
    """Structured behavioral simulation — not 'do you like this idea?'."""
    # Price acceptance: how does the monthly price compare to budget & sensitivity?
    price_ratio = price / max(persona.budget_monthly, 1.0)
    price_penalty = max(0.0, price_ratio - 0.1) * (0.5 + persona.price_sensitivity)

    positioning_boost = {
        "save time": 0.08,
        "AI co-pilot": 0.06 * persona.ai_trust * 2,
        "cheaper alternative": 0.07 * persona.price_sensitivity * 2,
        "best-in-class": 0.04,
    }.get(positioning.lower(), 0.02)

    interest = max(0.0, min(1.0,
        0.30 + persona.pain_severity * 0.40 + persona.technology_adoption * 0.15
        + positioning_boost - price_penalty * 0.3))
    trust = max(0.0, min(1.0, persona.ai_trust * 0.8 + 0.1))
    wtp = max(0.0, min(1.0, persona.willingness_to_pay - price_penalty))
    switching = max(0.0, min(1.0,
        interest * 0.6 + (0.3 if persona.current_solution == "manual" else 0.0)))
    recommendation = max(0.0, min(1.0, interest * 0.7 + trust * 0.3))

    objections: list[str] = []
    if price_penalty > 0.25:
        objections.append("too expensive for the value")
    if persona.ai_trust < 0.35:
        objections.append("does not trust AI with this task")
    if persona.current_solution.startswith("competitor"):
        objections.append(f"already using {persona.current_solution}")
    if round_num >= 2 and persona.risk_tolerance < 0.3:
        objections.append("prefers to wait for social proof")

    return PersonaReaction(
        persona_id=persona.persona_id,
        segment=persona.segment,
        interest=round(interest, 3),
        trust=round(trust, 3),
        willingness_to_try=round((interest + trust) / 2, 3),
        willingness_to_pay=round(wtp, 3),
        switching_probability=round(switching, 3),
        recommendation_likelihood=round(recommendation, 3),
        main_objections=objections,
        round=round_num,
    )


def run_simulation_round(personas: list[Persona], product: str, price: float, positioning: str,
                         round_num: int, influence_factor: float = 0.0) -> list[PersonaReaction]:
    """One simulation round. influence_factor models word-of-mouth/information exposure."""
    reactions = [simulate_reaction(p, product, price, positioning, round_num) for p in personas]
    if influence_factor > 0 and reactions:
        mean_interest = statistics.mean(r.interest for r in reactions)
        for r in reactions:
            r.interest = round(max(0.0, min(1.0, r.interest * (1 - influence_factor) + mean_interest * influence_factor)), 3)
    return reactions


def segment_summary(reactions: list[PersonaReaction]) -> dict[str, dict]:
    by_seg: dict[str, list[PersonaReaction]] = defaultdict(list)
    for r in reactions:
        by_seg[r.segment].append(r)
    summary = {}
    for seg, rs in by_seg.items():
        summary[seg] = {
            "count": len(rs),
            "interest": round(statistics.mean(r.interest for r in rs), 3),
            "willingness_to_pay": round(statistics.mean(r.willingness_to_pay for r in rs), 3),
            "switching": round(statistics.mean(r.switching_probability for r in rs), 3),
            "top_objection": _top_objection(rs),
        }
    return dict(sorted(summary.items(), key=lambda kv: kv[1]["interest"], reverse=True))


def _top_objection(rs: list[PersonaReaction]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for r in rs:
        for o in r.main_objections:
            counts[o] += 1
    return max(counts, key=counts.get) if counts else ""


def run_scenario_grid(personas: list[Persona], products: list[str], prices: list[float],
                      positionings: list[str], segments: list[str] | None = None) -> list[ScenarioResult]:
    """Test product x price x positioning scenarios against target segments."""
    pool = [p for p in personas if segments is None or p.segment in segments]
    results: list[ScenarioResult] = []
    for prod in products:
        for price in prices:
            for pos in positionings:
                reactions = run_simulation_round(pool, prod, price, pos, round_num=3)
                score = (
                    statistics.mean(r.interest for r in reactions) * 0.4
                    + statistics.mean(r.willingness_to_pay for r in reactions) * 0.35
                    + statistics.mean(r.switching_probability for r in reactions) * 0.25
                ) * 100
                results.append(ScenarioResult(
                    scenario_id=uuid.uuid4().hex[:8],
                    product=prod, price=price, positioning=pos,
                    segment=",".join(segments) if segments else "all",
                    mean_interest=round(statistics.mean(r.interest for r in reactions), 3),
                    mean_willingness_to_pay=round(statistics.mean(r.willingness_to_pay for r in reactions), 3),
                    mean_switching=round(statistics.mean(r.switching_probability for r in reactions), 3),
                    score=round(score, 1),
                ))
    results.sort(key=lambda s: s.score, reverse=True)
    return results


def synthetic_market_score(reactions: list[PersonaReaction], scenarios: list[ScenarioResult]) -> dict:
    """Aggregate into a clearly-labeled Synthetic Market Score."""
    best = scenarios[0] if scenarios else None
    demand = statistics.mean(r.interest for r in reactions) * 100
    trust = statistics.mean(r.trust for r in reactions) * 100
    pricing = statistics.mean(r.willingness_to_pay for r in reactions) * 100
    adoption = statistics.mean(r.willingness_to_try for r in reactions) * 100
    switching = statistics.mean(r.switching_probability for r in reactions) * 100
    overall = demand * 0.3 + adoption * 0.2 + pricing * 0.2 + trust * 0.15 + switching * 0.15
    return {
        "synthetic_market_score": round(overall, 1),
        "synthetic_demand_score": round(demand, 1),
        "synthetic_trust_score": round(trust, 1),
        "synthetic_pricing_score": round(pricing, 1),
        "synthetic_adoption_score": round(adoption, 1),
        "synthetic_switching_score": round(switching, 1),
        "best_scenario": best.model_dump() if best else None,
        "label": "SIMULATED",
    }
