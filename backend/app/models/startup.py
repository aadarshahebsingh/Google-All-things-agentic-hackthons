"""Startup idea understanding model."""
from datetime import datetime, timezone
from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Startup(BaseModel):
    startup_id: str
    raw_idea: str
    problem: str = ""
    solution: str = ""
    industry: str = ""
    target_customers: list[str] = Field(default_factory=list)
    geography: str = "global"
    business_model: str = ""
    likely_competitors: list[str] = Field(default_factory=list)
    initial_hypotheses: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    status: str = "CREATED"  # CREATED | RUNNING | COMPLETE | FAILED
    created_at: str = Field(default_factory=lambda: utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: utcnow().isoformat())
