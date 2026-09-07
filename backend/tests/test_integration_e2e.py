"""Integration test: idea → research → synthetic market → market fit (demo mode)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents.customer_discovery_agent import run_customer_discovery_agent  # noqa: E402
from app.agents.market_fit_agent import run_market_fit_agent  # noqa: E402
from app.agents.research_agent import run_research_agent  # noqa: E402
from app.agents.synthetic_market_agent import run_synthetic_market_agent  # noqa: E402
from app.services.firestore_service import get_firestore_service  # noqa: E402


def test_end_to_end_core_loop():
    sid = "test-e2e-1"
    fs = get_firestore_service()
    startup = {"startup_id": sid, "solution": "AI platform helping engineering students find internships",
               "problem": "Students struggle to find relevant internships"}
    fs.set("startups", sid, startup)

    research = run_research_agent(sid, startup["solution"])
    assert research["evidence_count"] > 0

    synthetic = run_synthetic_market_agent(sid, startup, research)
    assert synthetic["participant_count"] == 10000
    assert synthetic["scores"]["label"] == "SIMULATED"
    assert len(synthetic["segments"]) >= 3
    assert len(synthetic["scenario_scores"]) >= 5

    customer = run_customer_discovery_agent(sid, startup)
    assert customer["candidates_found"] == 3

    report = run_market_fit_agent(sid)
    assert 0 <= report["market_fit_score"] <= 100
    assert 0 <= report["confidence"] <= 100
    assert len(report["dimensions"]) == 8
    # No real interviews ran -> confidence should reflect that
    assert report["stream_scores"][3]["has_data"] is False

    hyps = fs.list("hypotheses", "startup_id", sid)
    assert len(hyps) >= 1
