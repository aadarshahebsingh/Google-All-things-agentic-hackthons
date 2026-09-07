"""Opportunity Engine: Hackathon + Investor agents, plus Calendar integration.

Seeded demo opportunities are clearly labeled DEMO. Calendar events are only
claimed as created when the adapter confirms it.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from ..models.opportunity import InvestorDraft, Opportunity
from ..services.event_service import log_event
from ..services.firestore_service import get_firestore_service
from ..tools.calendar_tools import schedule_opportunity_prep

DEMO_OPPORTUNITIES = [
    {"kind": "hackathon", "name": "Google All Things Agentic Hackathon",
     "fit_score": 96, "eligibility": "Global, teams or individuals",
     "url": "https://googlehackathons.com", "why_fit": "Agentic AI built on Google stack — direct match.",
     "days_to_deadline": 21},
    {"kind": "accelerator", "name": "AI Startup Accelerator — Winter Batch",
     "fit_score": 81, "eligibility": "Pre-seed AI startups",
     "url": "https://example-accelerator.com", "why_fit": "Early-stage AI validation tooling thesis.",
     "days_to_deadline": 45},
]


def run_hackathon_agent(startup_id: str) -> list[dict]:
    fs = get_firestore_service()
    log_event(startup_id, "HackathonAgent", "Discovering relevant opportunities")
    opps: list[dict] = []
    for seed in DEMO_OPPORTUNITIES:
        deadline = (datetime.now() + timedelta(days=seed["days_to_deadline"])).date().isoformat()
        opp = Opportunity(
            opportunity_id=uuid.uuid4().hex[:10],
            startup_id=startup_id,
            kind=seed["kind"], name=seed["name"], fit_score=seed["fit_score"],
            deadline=deadline, eligibility=seed["eligibility"],
            url=seed["url"], why_fit=seed["why_fit"], data_label="DEMO",
        )
        fs.add("hackathons", opp.model_dump(), doc_id=opp.opportunity_id)
        opps.append(opp.model_dump())
        # Automatically create calendar preparation timeline.
        cal_results = schedule_opportunity_prep(startup_id, opp)
        created = sum(1 for r in cal_results if r.get("status") in ("created", "already_exists"))
        backend = cal_results[0].get("backend") if cal_results else "none"
        log_event(startup_id, "CalendarAgent",
                  f"{created} events on {backend} for {opp.name}")
    fs.set("opportunities_meta", startup_id, {"startup_id": startup_id, "count": len(opps)})
    return opps


def run_investor_agent(startup_id: str) -> list[dict]:
    """Find investors and prepare drafts. NEVER auto-send — human confirmation required."""
    fs = get_firestore_service()
    log_event(startup_id, "InvestorAgent", "Finding high-fit investors")
    strategy = fs.get("strategy", startup_id) or {}
    fit = fs.get("market_fit", startup_id) or {}
    seeds = [
        {"name": "Demo Ventures (AI Seed)", "thesis": "AI agent infrastructure", "fit": 88},
        {"name": "Founder Fund I", "thesis": "Vertical AI SaaS, India", "fit": 74},
    ]
    drafts: list[dict] = []
    for s in seeds:
        draft = InvestorDraft(
            draft_id=uuid.uuid4().hex[:10],
            startup_id=startup_id,
            investor_name=s["name"],
            thesis_fit=s["thesis"],
            fit_score=s["fit"],
            draft_message=(f"Hi {s['name']} team — we're building validation tooling for "
                           f"{strategy.get('icp', 'founders')} with Market Fit "
                           f"{fit.get('market_fit_score', 'N/A')}/100 and evidence from research, "
                           f"simulation and real interviews. Open to a short call? "
                           f"(Draft — requires human confirmation before sending.)"),
        )
        fs.add("investors", draft.model_dump(), doc_id=draft.draft_id)
        drafts.append(draft.model_dump())
    log_event(startup_id, "InvestorAgent", f"{len(drafts)} investor drafts prepared (pending human confirmation)")
    return drafts
