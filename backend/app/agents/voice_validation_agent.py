"""Voice Validation Agent — independent stream D.

Conducts a dynamic, consent-gated interview via a modular VoiceProvider
adapter (Twilio real / Demo simulated). Produces structured interview results.
"""
from __future__ import annotations

import uuid

from ..models.customer import ConsentRecord, Interview
from ..services.event_service import log_event
from ..services.firestore_service import get_firestore_service
from ..tools.voice_tools import get_voice_provider

INTERVIEW_SCRIPT = [
    {"intent": "current_process", "text": "How do you currently approach this problem today?"},
    {"intent": "frustration", "text": "What is the most frustrating part of the current process?"},
    {"intent": "personalization", "text": "How useful would automated, personalized recommendations be for you?"},
    {"intent": "trust_automation", "text": "Would you trust AI to handle parts of this automatically?"},
    {"intent": "pricing", "text": "What would you reasonably pay per month for this?"},
    {"intent": "objection", "text": "What would stop you from using such a product?"},
]


def grant_consent(startup_id: str, candidate_id: str) -> ConsentRecord:
    """Record explicit consent BEFORE any voice interaction."""
    fs = get_firestore_service()
    consent = ConsentRecord(
        consent_id=uuid.uuid4().hex[:10],
        startup_id=startup_id,
        candidate_id=candidate_id,
        status="granted",
    )
    fs.add("consents", consent.model_dump(), doc_id=consent.consent_id)
    log_event(startup_id, "ConsentSystem", f"Consent granted by {candidate_id}")
    return consent


def has_consent(startup_id: str, candidate_id: str) -> bool:
    consents = get_firestore_service().list("consents", "candidate_id", candidate_id)
    return any(c.get("status") == "granted" and c.get("startup_id") == startup_id for c in consents)


def run_voice_interview(startup_id: str, candidate_id: str, hypotheses: list[str] | None = None) -> dict:
    """Run interview ONLY after explicit consent. Returns structured result."""
    fs = get_firestore_service()
    if not has_consent(startup_id, candidate_id):
        return {"status": "error", "error_code": "CONSENT_REQUIRED",
                "message": "Voice interviews require explicit recorded consent.", "retryable": False}

    provider = get_voice_provider()
    log_event(startup_id, "VoiceValidationAgent", f"Starting {provider.name} voice interview")
    call = provider.place_call(candidate_id, INTERVIEW_SCRIPT)
    if call.get("status") == "error":
        log_event(startup_id, "VoiceValidationAgent", f"Call failed: {call}", level="ERROR")
        return call

    responses = call.get("responses", [])
    transcript = [{"q": r["question"], "a": r["answer"], "simulated": r.get("simulated", False)}
                  for r in responses]

    # Deterministic analysis of answers (keyword scoring on transcript).
    joined = " ".join(r["answer"].lower() for r in responses)
    pain = _score(joined, ["slow", "waste", "frustrat", "hours", "weeks", "irrelevant"])
    interest = _score(joined, ["useful", "gap", "recommendation", "would be"])
    trust = _score(joined, ["trust", "review", "accurate"]) * 0.7
    confirmed = pain >= 0.5

    supported, rejected = [], []
    for h in hypotheses or []:
        (supported if confirmed else rejected).append(h)

    consent = next((c for c in fs.list("consents", "candidate_id", candidate_id)
                    if c.get("startup_id") == startup_id), {})
    interview = Interview(
        interview_id=uuid.uuid4().hex[:10],
        startup_id=startup_id,
        candidate_id=candidate_id,
        consent_id=consent.get("consent_id", ""),
        provider=provider.name,
        problem_confirmed=confirmed,
        pain_score=pain * 10,
        interest_score=interest * 10,
        trust_score=max(trust, 0.4) * 10,
        willingness_to_pay=_extract_price(joined),
        objections=[r["answer"] for r in responses if r.get("intent") == "objection"],
        quotes=[r["answer"] for r in responses[:2]],
        insights=["Pain centers on time wasted filtering irrelevant options."],
        hypotheses_supported=supported,
        hypotheses_rejected=rejected,
        transcript=transcript,
    )
    fs.add("interviews", interview.model_dump(), doc_id=interview.interview_id)
    fs.update("customers", candidate_id, {"outreach_status": "INTERVIEWED"})
    label = "SIMULATED" if provider.name == "demo" else "REAL"
    log_event(startup_id, "VoiceValidationAgent",
              f"Interview complete ({label}); pain={interview.pain_score:.0f}/10")
    return interview.model_dump()


def _score(text: str, keywords: list[str]) -> float:
    hits = sum(1 for k in keywords if k in text)
    return min(1.0, hits / max(len(keywords) * 0.6, 1))


def _extract_price(text: str) -> str:
    import re

    m = re.search(r"(\d+)", text)
    return f"₹{m.group(1)}/month" if m else "unknown"
