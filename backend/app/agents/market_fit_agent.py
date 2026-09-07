"""Market Fit Synthesis Agent — reconciles the four independent evidence streams."""
from __future__ import annotations
import uuid
from ..models.hypothesis import Hypothesis
from ..services.event_service import log_event
from ..services.firestore_service import get_firestore_service
from ..services.market_fit_service import compute_market_fit


def run_market_fit_agent(startup_id: str) -> dict:
    fs = get_firestore_service()
    log_event(startup_id, "MarketFitAgent", "Reconciling evidence from all streams")

    research = fs.get("research", startup_id)
    synthetic = fs.get("simulations", startup_id)
    customer = fs.get("customers_meta", startup_id)
    interviews = [i for i in fs.list("interviews", "startup_id", startup_id)]

    report = compute_market_fit(startup_id, research, synthetic, customer, interviews)
    fs.set("market_fit", startup_id, report.model_dump())
    log_event(startup_id, "MarketFitAgent",
              f"Market Fit {report.market_fit_score}/100, confidence {report.confidence}%")

    _update_hypotheses(startup_id, research or {}, synthetic or {}, interviews)
    return report.model_dump()


def _update_hypotheses(startup_id: str, research: dict, synthetic: dict, interviews: list[dict]) -> None:
    """Create/update hypothesis records from evidence across streams."""
    fs = get_firestore_service()
    existing = {h["statement"]: h for h in fs.list("hypotheses", "startup_id", startup_id)}

    def upsert(statement: str, ev_for: str | None, ev_against: str | None) -> None:
        h = existing.get(statement) or Hypothesis(
            hypothesis_id=uuid.uuid4().hex[:8],
            startup_id=startup_id,
            statement=statement,
        ).model_dump()
        if ev_for:
            h.setdefault("evidence_for", []).append(ev_for)
        if ev_against:
            h.setdefault("evidence_against", []).append(ev_against)
        n_for = len(h.get("evidence_for", []))
        n_against = len(h.get("evidence_against", []))
        h["confidence"] = max(5, min(95, 50 + (n_for - n_against) * 15))
        h["status"] = "SUPPORTED" if h["confidence"] >= 70 else ("REJECTED" if h["confidence"] <= 30 else "UNCERTAIN")
        h["next_validation_action"] = f"Validate with real customers: '{statement}'"
        fs.set("hypotheses", h["hypothesis_id"], h)
        existing[statement] = h

    best_price = ((synthetic.get("scores") or {}).get("best_scenario") or {}).get("price")
    if best_price is not None:
        upsert(f"Customers will pay ₹{best_price}/month",
               f"Synthetic market WTP score {(synthetic.get('scores') or {}).get('synthetic_pricing_score')}",
               None)
    for iv in interviews:
        for hs in iv.get("hypotheses_supported", []):
            upsert(hs, f"Interview {iv['interview_id']} confirmed", None)
        for hr in iv.get("hypotheses_rejected", []):
            upsert(hr, None, f"Interview {iv['interview_id']} rejected")
    if research.get("strong_signals"):
        upsert(str(research["strong_signals"][0])[:120], "Research evidence", None)
