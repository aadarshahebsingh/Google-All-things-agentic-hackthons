"""Research Agent — real-world evidence gathering (independent stream A)."""
from __future__ import annotations

from ..models.evidence import Evidence
from ..services.event_service import log_event
from ..services.firestore_service import get_firestore_service
from ..tools.research_tools import RESEARCH_AREAS, gather_research_evidence


def run_research_agent(startup_id: str, idea_summary: str) -> dict:
    """Gather cited evidence across research areas. Returns structured result."""
    log_event(startup_id, "ResearchAgent", "Searching market evidence")
    fs = get_firestore_service()
    all_evidence: list[Evidence] = []
    by_area = gather_research_evidence(startup_id, idea_summary, RESEARCH_AREAS)

    for area, items in by_area.items():
        for ev in items:
            fs.add("evidence", ev.model_dump(), doc_id=ev.evidence_id)
            all_evidence.append(ev)
        log_event(startup_id, "ResearchAgent", f"{area}: {len(items)} evidence items")

    n = len(all_evidence)
    # Deterministic scoring from evidence quality, not LLM invention.
    avg_conf = sum(e.confidence for e in all_evidence) / n if n else 0
    real_sources = sum(1 for e in all_evidence if e.source_type not in ("demo_cache",))
    coverage = len(by_area) / len(RESEARCH_AREAS)
    research_score = round(min(100.0, (avg_conf * 60 + coverage * 40) * (0.7 + 0.3 * min(1, real_sources / 6))), 1)

    result = {
        "research_score": research_score,
        "evidence_count": n,
        "confidence": round(research_score * 0.8, 1),
        "strong_signals": [e.claim for e in all_evidence if e.confidence >= 0.6][:5],
        "weak_signals": [e.claim for e in all_evidence if e.confidence < 0.6][:5],
        "unknowns": ["Exact TAM/SAM/SOM figures require licensed market data"],
        "dimension_hints": _dimension_hints(all_evidence, coverage),
        "label": "REAL" if real_sources else "DEMO",
    }
    fs.set("research", startup_id, {"startup_id": startup_id, **result})
    log_event(startup_id, "ResearchAgent", f"{n} evidence items found; score {research_score}")
    return result


def _dimension_hints(evidence: list[Evidence], coverage: float) -> dict[str, float]:
    """Map evidence coverage to dimension hints (conservative, evidence-based)."""
    return {
        "problem_severity": round(50 + coverage * 20, 1),
        "market_growth": round(45 + coverage * 25, 1),
        "competition": round(50 + coverage * 15, 1),
    }
