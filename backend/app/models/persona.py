"""Synthetic persona and population models."""
from pydantic import BaseModel, Field
from .startup import utcnow


class PopulationModel(BaseModel):
    """Market population distributions, grounded in research."""
    age_distribution: dict[str, float] = Field(default_factory=dict)
    location_distribution: dict[str, float] = Field(default_factory=dict)
    income_distribution: dict[str, float] = Field(default_factory=dict)
    experience_distribution: dict[str, float] = Field(default_factory=dict)
    ai_trust_distribution: dict[str, float] = Field(default_factory=dict)
    price_sensitivity_distribution: dict[str, float] = Field(default_factory=dict)
    current_solution_distribution: dict[str, float] = Field(default_factory=dict)
    pain_severity_distribution: dict[str, float] = Field(default_factory=dict)


class Persona(BaseModel):
    persona_id: str
    startup_id: str
    segment: str = "general"
    demographics: dict = Field(default_factory=dict)
    occupation: str = ""
    goals: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    current_solution: str = ""
    budget_monthly: float = 0.0
    ai_trust: float = 0.5
    price_sensitivity: float = 0.5
    risk_tolerance: float = 0.5
    technology_adoption: float = 0.5
    automation_preference: float = 0.5
    pain_severity: float = 0.5
    willingness_to_pay: float = 0.5
    beliefs: list[str] = Field(default_factory=list)
    memory: list[str] = Field(default_factory=list)


class PersonaReaction(BaseModel):
    persona_id: str
    segment: str
    interest: float
    trust: float
    willingness_to_try: float
    willingness_to_pay: float
    switching_probability: float
    recommendation_likelihood: float = 0.0
    main_objections: list[str] = Field(default_factory=list)
    round: int = 1
    timestamp: str = Field(default_factory=lambda: utcnow().isoformat())


class ScenarioResult(BaseModel):
    scenario_id: str
    product: str
    price: float
    positioning: str
    segment: str
    mean_interest: float
    mean_willingness_to_pay: float
    mean_switching: float
    score: float
