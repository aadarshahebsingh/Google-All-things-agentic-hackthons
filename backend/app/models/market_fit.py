"""Market fit synthesis models."""
from pydantic import BaseModel, Field
from .startup import utcnow

DIMENSIONS = [
    "problem_severity",
    "demand",
    "market_growth",
    "competition",
    "differentiation",
    "pricing",
    "trust",
    "customer_validation",
]

DEFAULT_WEIGHTS: dict[str, float] = {
    "problem_severity": 0.18,
    "demand": 0.17,
    "market_growth": 0.12,
    "competition": 0.10,
    "differentiation": 0.12,
    "pricing": 0.10,
    "trust": 0.08,
    "customer_validation": 0.13,
}


class DimensionScore(BaseModel):
    dimension: str
    research_evidence: dict = Field(default_factory=dict)
    synthetic_evidence: dict = Field(default_factory=dict)
    customer_evidence: dict = Field(default_factory=dict)
    voice_evidence: dict = Field(default_factory=dict)
    final_score: float = 0.0   # 0-100
    confidence: float = 0.0    # 0-100


class EvidenceConflict(BaseModel):
    conflict_id: str
    dimension: str
    sources_disagreeing: list[str]
    description: str
    possible_reasons: list[str] = Field(default_factory=list)
    stronger_source: str = ""
    next_validation: str = ""


class StreamScore(BaseModel):
    stream: str          # research | synthetic | customer | voice
    score: float = 0.0   # 0-100
    has_data: bool = False
    label: str = "REAL"  # REAL | SIMULATED | DEMO


class MarketFitReport(BaseModel):
    startup_id: str
    market_fit_score: float = 0.0
    confidence: float = 0.0
    dimensions: list[DimensionScore] = Field(default_factory=list)
    stream_scores: list[StreamScore] = Field(default_factory=list)
    conflicts: list[EvidenceConflict] = Field(default_factory=list)
    consensus: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    best_customer: str = ""
    best_pricing_hypothesis: str = ""
    biggest_risk: str = ""
    recommendation: str = ""
    next_validation: str = ""
    weights_used: dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    timestamp: str = Field(default_factory=lambda: utcnow().isoformat())
