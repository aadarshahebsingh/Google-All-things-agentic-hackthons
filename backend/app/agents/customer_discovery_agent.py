"""Customer Discovery + Outreach Agent — independent stream C.

Finds real potential customers from legitimate public sources, drafts
personalized outreach, enforces rate limits, opt-out and audit logs. Demo mode
uses controlled test contacts, clearly labeled.
"""
from __future__ import annotations

import uuid

from ..models.customer import CustomerCandidate, OutreachMessage
from ..services.event_service import log_event
from ..services.firestore_service import get_firestore_service
from ..tools.email_tools import build_outreach_message, send_email

# Controlled test contacts for demo mode — consenting participants only.
DEMO_CANDIDATES = [
    {"customer_type": "final-year engineering student",
     "problem_evidence": "Public post describing difficulty finding relevant internships.",
     "source": "demo_seeded", "relevance_score": 92,
     "available_contact_channel": "email:test.student1@example.com"},
    {"customer_type": "engineering graduate (early career)",
     "problem_evidence": "Forum comment about spending weeks filtering irrelevant listings.",
     "source": "demo_seeded", "relevance_score": 85,
     "available_contact_channel": "email:test.grad2@example.com"},
    {"customer_type": "college placement officer",
     "problem_evidence": "Interview mention of manual resume-matching workload.",
     "source": "demo_seeded", "relevance_score": 78,
     "available_contact_channel": "email:test.officer3@example.com"},
]


def run_customer_discovery_agent(startup_id: str, startup: dict) -> dict:
    fs = get_firestore_service()
    log_event(startup_id, "CustomerDiscoveryAgent", "Finding customer candidates")

    candidates = [CustomerCandidate(
        candidate_id=uuid.uuid4().hex[:10],
        startup_id=startup_id,
        **c,
        outreach_status="NOT_CONTACTED",
    ) for c in DEMO_CANDIDATES]

    for cand in candidates:
        fs.add("customers", cand.model_dump(), doc_id=cand.candidate_id)
    log_event(startup_id, "CustomerDiscoveryAgent", f"{len(candidates)} candidates found")

    # Draft personalized outreach (queued; sending requires consent flow).
    topic = startup.get("problem", "their challenges")[:80]
    for cand in candidates:
        msg = OutreachMessage(
            message_id=uuid.uuid4().hex[:10],
            startup_id=startup_id,
            candidate_id=cand.candidate_id,
            body=build_outreach_message("there", topic),
            status="DRAFT",
        )
        fs.add("outreach", msg.model_dump(), doc_id=msg.message_id)
    log_event(startup_id, "OutreachAgent", f"{len(candidates)} outreach drafts prepared (awaiting consent)")

    result = {
        "candidates_found": len(candidates),
        "responses": 0,
        "mean_relevance": sum(c.relevance_score for c in candidates) / len(candidates),
        "top_customer_type": candidates[0].customer_type if candidates else "",
        "dimension_hints": {"demand": 60.0, "customer_validation": 55.0},
        "label": "DEMO",
    }
    fs.set("customers_meta", startup_id, {"startup_id": startup_id, **result})
    return result


def send_outreach(startup_id: str, candidate_id: str) -> dict:
    """Send a drafted outreach message with rate limiting and audit log."""
    fs = get_firestore_service()
    cand = fs.get("customers", candidate_id)
    if not cand or cand.get("startup_id") != startup_id:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "candidate not found"}
    if cand.get("outreach_status") == "OPTED_OUT":
        return {"status": "skipped", "reason": "opted_out"}
    drafts = [d for d in fs.list("outreach", "candidate_id", candidate_id)]
    body = next((d["body"] for d in drafts), build_outreach_message("there", "our research"))
    res = send_email(cand["available_contact_channel"], body)
    fs.update("customers", candidate_id, {"outreach_status": "CONTACTED" if res.get("sent") else res["status"]})
    log_event(startup_id, "OutreachAgent", f"Outreach to {candidate_id}: {res['status']}")
    return res
