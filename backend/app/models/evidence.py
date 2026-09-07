"""Evidence model — every claim must carry provenance."""
from pydantic import BaseModel, Field
from .startup import utcnow


class Evidence(BaseModel):
    evidence_id: str
    startup_id: str
    claim: str
    source_url: str | None = None
    source_title: str | None = None
    source_type: str = "web"  # web | report | demo_cache | synthetic | interview
    evidence_text: str = ""
    confidence: float = 0.5
    relevance: float = 0.5
    timestamp: str = Field(default_factory=lambda: utcnow().isoformat())
    stream: str = "research"  # research | synthetic | customer | voice
