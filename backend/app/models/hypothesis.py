"""Hypothesis tracker models."""
from pydantic import BaseModel, Field
from .startup import utcnow


class Hypothesis(BaseModel):
    hypothesis_id: str
    startup_id: str
    statement: str
    status: str = "UNCERTAIN"  # SUPPORTED | UNCERTAIN | REJECTED
    evidence_for: list[str] = Field(default_factory=list)
    evidence_against: list[str] = Field(default_factory=list)
    confidence: int = 50  # 0-100
    next_validation_action: str = ""
    updated_at: str = Field(default_factory=lambda: utcnow().isoformat())
