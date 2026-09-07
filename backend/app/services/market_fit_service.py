"""Deterministic market-fit synthesis: dimension scoring, confidence model,
evidence conflict detection and hypothesis updates.

The final score is computed from structured dimension scores with configurable
weights — the LLM never invents the number.
"""
from __future__ import annotations

import uuid
from statistics import mean

from ..models.market_fit import (
    DEFAULT_WEIGHTS,
    DIMENSIONS,
    DimensionScore,
    EvidenceConflict,
    MarketFitReport,
    StreamScore,
)
from ..models.persona import ScenarioResult

# Confidence weights per stream. Missing real-customer evidence lowers
# confidence but does not fabricate data.
STREAM_CONFIDENCE_WEIGHTS = {
    "research": 0.30,
    "synthetic": 0.20,
    "customer": 0.25,
    "voice": 0.25,
}


def _norm(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(0.0, min(100.0, (value - lo) / (hi - lo) * 100))


def compute_market_fit(
    startup_id: str,
    research_result: dict | None,
    synthetic_result: dict | None,
    customer_result: dict | None,
    voice_results: list[dict],
) -> MarketFitReport:
    """Reconcile four independent evidence streams into a Market Fit report."""
    research = research_result or {}
    synthetic = synthetic_result or {}
    customer = customer_result or {}
    has_voice = bool(voice_results)

    # ---- Stream scores -------------------------------------------------
    research_score = float(research.get("research_score", 0)) if research else 0.0
    synth_scores = synthetic.get("scores", {}) if synthetic else {}
    synthetic_score = float(synth_scores.get("synthetic_market_score", 0))
    customer_score = _customer_stream_score(customer)
    voice_score = _voice_stream_score(voice_results)

    streams = [
        StreamScore(stream="research", score=research_score, has_data=bool(research), label="REAL"),
        StreamScore(stream="synthetic", score=synthetic_score, has_data=bool(synthetic), label="SIMULATED"),
        StreamScore(stream="customer", score=customer_score, has_data=bool(customer), label="REAL"),
        StreamScore(stream="voice", score=voice_score, has_data=has_voice, label="REAL"),
    ]

    # ---- Dimension scores ---------------------------------------------
    dims: list[DimensionScore] = []
    for dim in DIMENSIONS:
        d = DimensionScore(dimension=dim)
        d.research_evidence = {"score": research.get("dimension_hints", {}).get(dim), "present": dim in research.get("dimension_hints", {})}
        d.synthetic_evidence = {"score": _synthetic_dim(dim, synth_scores), "present": True}
        d.customer_evidence = {"score": customer.get("dimension_hints", {}).get(dim), "present": dim in customer.get("dimension_hints", {})}
        voice_scores = [v["dimension_hints"].get(dim, 0) for v in voice_results if v.get("dimension_hints")]
        d.voice_evidence = {"score": mean(voice_scores) if voice_scores else None,
                            "present": has_voice}

        parts: list[float] = []
        if d.research_evidence["present"] and d.research_evidence["score"] is not None:
            parts.append(float(d.research_evidence["score"]))
        if d.customer_evidence["present"] and d.customer_evidence["score"] is not None:
            parts.append(float(d.customer_evidence["score"]))
        if d.voice_evidence["present"] and d.voice_evidence["score"] is not None:
            parts.append(float(d.voice_evidence["score"]))
        syn = _synthetic_dim(dim, synth_scores)
        if syn is not None:
            parts.append(syn)

        # Weighted: real evidence counts double vs synthetic.
        real_parts = ([float(d.research_evidence["score"])] if d.research_evidence["present"] and d.research_evidence["score"] is not None else []) + \
                     ([float(d.customer_evidence["score"])] if d.customer_evidence["present"] and d.customer_evidence["score"] is not None else []) + \
                     ([float(d.voice_evidence["score"])] if d.voice_evidence["present"] and d.voice_evidence["score"] is not None else [])
        sim_parts = [syn] if syn is not None else []

        if real_parts and sim_parts:
            d.final_score = round(mean(real_parts) * 2 / 3 + mean(sim_parts) / 3, 1)
        elif real_parts:
            d.final_score = round(mean(real_parts), 1)
        elif sim_parts:
            d.final_score = round(mean(sim_parts), 1)
        else:
            d.final_score = 50.0  # neutral when nothing known — flagged as unknown

        # Per-dimension confidence: how many independent sources agree.
        n_sources = len(real_parts) + len(sim_parts)
        agreement_bonus = 10 if len(real_parts) >= 2 else 0
        d.confidence = min(95.0, n_sources * 22 + agreement_bonus)
        dims.append(d)

    conflicts = detect_conflicts(startup_id, dims, streams)

    # ---- Overall score & confidence ------------------------------------
    weights = dict(DEFAULT_WEIGHTS)
    overall = sum(d.final_score * weights[d.dimension] for d in dims if d.dimension in weights)
    overall += sum(d.final_score for d in dims if d.dimension not in weights) / max(len(dims), 1) * 0.0

    conf_components = []
    for s in streams:
        if s.has_data:
            conf_components.append((s.score if s.stream != "synthetic" else min(s.score, 70), STREAM_CONFIDENCE_WEIGHTS[s.stream]))
    base_confidence = sum(v for _, v in conf_components) / sum(STREAM_CONFIDENCE_WEIGHTS.values()) if conf_components else 0
    # Real direct validation boosts confidence; its absence caps it.
    direct_validation = (1 if customer.get("candidates_found") else 0) + (2 if has_voice else 0)
    confidence = min(95.0, base_confidence * (0.55 + 0.15 * direct_validation))

    best_scenario = (synthetic.get("best_scenario") or {})
    report = MarketFitReport(
        startup_id=startup_id,
        market_fit_score=round(overall, 1),
        confidence=round(confidence, 1),
        dimensions=dims,
        stream_scores=streams,
        conflicts=conflicts,
        consensus=_consensus(dims),
        unknowns=_unknowns(dims, streams),
        best_customer=(customer.get("top_customer_type") or best_scenario.get("segment") or ""),
        best_pricing_hypothesis=str(best_scenario.get("price", "")) + "/month" if best_scenario else "",
        biggest_risk=_biggest_risk(dims),
        recommendation=_recommendation(dims, best_scenario),
        next_validation=_next_validation(conflicts, dims),
        weights_used=weights,
    )
    return report


def _synthetic_dim(dim: str, scores: dict) -> float | None:
    mapping = {
        "demand": "synthetic_demand_score",
        "trust": "synthetic_trust_score",
        "pricing": "synthetic_pricing_score",
        "problem_severity": "synthetic_demand_score",
        "customer_validation": "synthetic_adoption_score",
        "differentiation": "synthetic_switching_score",
        "market_growth": None,
        "competition": None,
    }
    key = mapping.get(dim)
    return float(scores[key]) if key and key in scores else None


def _customer_stream_score(customer: dict) -> float:
    candidates = customer.get("candidates_found", 0)
    responded = customer.get("responses", 0)
    relevance = customer.get("mean_relevance", 0)
    if not candidates:
        return 0.0
    reach = min(1.0, candidates / 20) * 60
    response_rate = (responded / candidates) if candidates else 0
    return round(reach + response_rate * 25 + relevance * 0.15, 1)


def _voice_stream_score(voices: list[dict]) -> float:
    if not voices:
        return 0.0
    per_call = []
    for v in voices:
        confirmed = 100 if v.get("problem_confirmed") else 40
        pain = v.get("pain_score", 0) * 10
        interest = v.get("interest_score", 0) * 10
        trust = v.get("trust_score", 0) * 10
        per_call.append(confirmed * 0.3 + pain * 0.25 + interest * 0.25 + trust * 0.2)
    coverage = min(1.0, len(voices) / 5)  # saturates at 5 interviews
    return round(mean(per_call) * (0.6 + 0.4 * coverage), 1)


def detect_conflicts(startup_id: str, dims: list[DimensionScore], streams: list[StreamScore]) -> list[EvidenceConflict]:
    """Never hide disagreement between evidence sources."""
    conflicts: list[EvidenceConflict] = []
    for d in dims:
        vals: dict[str, float | None] = {
            "research": d.research_evidence.get("score"),
            "synthetic": d.synthetic_evidence.get("score"),
            "customer": d.customer_evidence.get("score"),
            "voice": d.voice_evidence.get("score"),
        }
        present = {k: v for k, v in vals.items() if v is not None}
        if len(present) < 2:
            continue
        hi = max(present.values())
        lo = min(present.values())
        if hi - lo >= 25:  # significant disagreement threshold
            disagreeing = [k for k, v in present.items() if abs(v - hi) < 5 or abs(v - lo) < 5]
            stronger = max(present, key=lambda k: present[k])
            conflicts.append(EvidenceConflict(
                conflict_id=uuid.uuid4().hex[:8],
                dimension=d.dimension,
                sources_disagreeing=list(present.keys()),
                description=f"{d.dimension}: {', '.join(f'{k}={v:.0f}' for k, v in present.items())}. "
                            f"Sources disagree by {hi - lo:.0f} points.",
                possible_reasons=[
                    "synthetic personas may overestimate enthusiasm",
                    "real customers face switching costs not captured in simulation",
                    "research sources may reflect different geographies/segments",
                ],
                stronger_source=stronger,
                next_validation=f"Run targeted validation on '{d.dimension}' with 5-10 real customers.",
            ))
    return conflicts


def _consensus(dims: list[DimensionScore]) -> list[str]:
    return [f"{d.dimension}: {d.final_score:.0f}" for d in dims if d.confidence >= 44]


def _unknowns(dims: list[DimensionScore], streams: list[StreamScore]) -> list[str]:
    out = [f"No data from '{s.stream}' stream" for s in streams if not s.has_data]
    out += [f"'{d.dimension}' lacks real-world evidence" for d in dims
            if not d.customer_evidence["present"] and not d.voice_evidence["present"]]
    return out


def _biggest_risk(dims: list[DimensionScore]) -> str:
    weakest = min(dims, key=lambda d: d.final_score)
    return f"Lowest-scoring dimension: {weakest.dimension} ({weakest.final_score:.0f}/100)"


def _recommendation(dims: list[DimensionScore], best_scenario: dict) -> str:
    strong = sorted(dims, key=lambda d: d.final_score, reverse=True)[:2]
    weak = sorted(dims, key=lambda d: d.final_score)[:1]
    rec = f"Double down on strengths ({strong[0].dimension}, {strong[1].dimension}); address {weak[0].dimension} first."
    if best_scenario:
        rec += f" Leading scenario: {best_scenario.get('product')} @ {best_scenario.get('price')} ({best_scenario.get('positioning')})."
    return rec


def _next_validation(conflicts: list[EvidenceConflict], dims: list[DimensionScore]) -> str:
    if conflicts:
        return conflicts[0].next_validation
    weak = sorted(dims, key=lambda d: d.confidence)[0]
    return f"Increase confidence on '{weak.dimension}' via additional real customer interviews."
