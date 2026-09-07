"""Customer discovery, outreach, consent and interview models."""
from pydantic import BaseModel, Field
from .startup import utcnow


class CustomerCandidate(BaseModel):
    candidate_id: str
    startup_id: str
    customer_type: str = ""
    problem_evidence: str = ""
    source: str = ""
    relevance_score: int = 0  # 0-100
    available_contact_channel: str = ""  # e.g. "email:test@example.com"
    outreach_status: str = "NOT_CONTACTED"  # NOT_CONTACTED | QUEUED | CONTACTED | OPTED_OUT | INTERVIEWED


class ConsentRecord(BaseModel):
    consent_id: str
    startup_id: str
    candidate_id: str
    consent_type: str = "voice_interview"
    timestamp: str = Field(default_factory=lambda: utcnow().isoformat())
    status: str = "granted"  # granted | denied | revoked


class OutreachMessage(BaseModel):
    message_id: str
    startup_id: str
    candidate_id: str
    channel: str = "email"
    body: str = ""
    status: str = "DRAFT"  # DRAFT | SENT | FAILED | SKIPPED_RATE_LIMITED
    timestamp: str = Field(default_factory=lambda: utcnow().isoformat())


class Interview(BaseModel):
    interview_id: str
    startup_id: str
    candidate_id: str
    consent_id: str
    provider: str = "demo"  # demo | twilio
    problem_confirmed: bool = False
    pain_score: float = 0.0      # 0-10
    interest_score: float = 0.0  # 0-10
    trust_score: float = 0.0     # 0-10
    willingness_to_pay: str = ""
    objections: list[str] = Field(default_factory=list)
    quotes: list[str] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
    hypotheses_supported: list[str] = Field(default_factory=list)
    hypotheses_rejected: list[str] = Field(default_factory=list)
    transcript: list[dict] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: utcnow().isoformat())
