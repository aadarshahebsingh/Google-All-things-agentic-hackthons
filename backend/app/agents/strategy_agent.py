"""Strategy Agent — evidence-based ICP, positioning, MVP, GTM, roadmap."""
from __future__ import annotations

from ..services.event_service import log_event
from ..services.firestore_service import get_firestore_service


def run_strategy_agent(startup_id: str) -> dict:
    fs = get_firestore_service()
    log_event(startup_id, "StrategyAgent", "Generating strategy from market-fit evidence")
    fit = fs.get("market_fit", startup_id) or {}
    synthetic = fs.get("simulations", startup_id) or {}
    customer = fs.get("customers_meta", startup_id) or {}

    dims = {d["dimension"]: d["final_score"] for d in fit.get("dimensions", [])}
    best_scenario = ((synthetic.get("scores") or {}).get("best_scenario") or {})

    strategy = {
        "startup_id": startup_id,
        "icp": customer.get("top_customer_type") or fit.get("best_customer") or "early adopters with severe pain",
        "value_proposition": f"Address the strongest validated dimension first: "
                             f"{max(dims, key=dims.get) if dims else 'core problem'} "
                             f"({max(dims.values()) if dims else 50:.0f}/100).",
        "positioning": best_scenario.get("positioning", "save time"),
        "pricing_hypothesis": f"₹{best_scenario.get('price', 99)}/month (hypothesis — validate with real users)",
        "mvp_scope": _mvp_scope(dims),
        "gtm": ["Target the highest-interest segment from the synthetic market",
                "Run 5-10 real discovery interviews",
                "Iterate pricing based on WTP evidence"],
        "risks": [fit.get("biggest_risk", "unknown")] + [
            c["description"] for c in fit.get("conflicts", [])[:2]],
        "roadmap": [
            {"phase": "V1", "focus": "Core matching/automation for ICP"},
            {"phase": "V1.1", "focus": "Pricing experiment ₹99 vs ₹199"},
            {"phase": "V2", "focus": "Expand to adjacent segments"},
        ],
    }
    fs.set("strategy", startup_id, strategy)
    log_event(startup_id, "StrategyAgent", "Strategy generated")
    return strategy


def _mvp_scope(dims: dict[str, float]) -> dict:
    must = [k for k, v in sorted(dims.items(), key=lambda kv: -kv[1])[:3]]
    later = [k for k, v in dims.items() if v < 60]
    return {
        "must_have": must or ["core problem solution"],
        "should_have": ["onboarding", "feedback loop"],
        "later": later,
        "do_not_build": ["features not supported by any evidence stream"],
    }
