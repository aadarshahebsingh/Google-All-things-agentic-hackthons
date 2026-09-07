"""Opportunity (hackathon/investor), task, alert and event-log models."""
from pydantic import BaseModel, Field
from .startup import utcnow


class Opportunity(BaseModel):
    opportunity_id: str
    startup_id: str
    kind: str = "hackathon"  # hackathon | accelerator | investor | competition
    name: str
    fit_score: int = 0       # 0-100
    deadline: str | None = None
    eligibility: str = ""
    url: str = ""
    why_fit: str = ""
    data_label: str = "DEMO"  # REAL | DEMO — never misrepresent seeded data


class InvestorDraft(BaseModel):
    draft_id: str
    startup_id: str
    investor_name: str
    thesis_fit: str = ""
    fit_score: int = 0
    draft_message: str = ""
    status: str = "PENDING_HUMAN_CONFIRMATION"


class TaskItem(BaseModel):
    task_id: str
    startup_id: str
    title: str
    due_date: str | None = None
    priority: str = "MEDIUM"
    reason: str = ""
    status: str = "OPEN"


class CompetitorAlert(BaseModel):
    alert_id: str
    startup_id: str
    competitor: str
    change: str
    impact: str = "LOW"  # HIGH | MEDIUM | LOW
    recommended_response: str = ""
    detected_at: str = Field(default_factory=lambda: utcnow().isoformat())


class AgentEvent(BaseModel):
    event_id: str
    startup_id: str
    workflow_id: str = ""
    agent: str
    message: str
    level: str = "INFO"
    timestamp: str = Field(default_factory=lambda: utcnow().isoformat())
