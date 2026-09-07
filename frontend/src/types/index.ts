// Shared types for the FounderShortcut API contract.
export interface AgentEvent {
  event_id: string;
  startup_id: string;
  agent: string;
  message: string;
  level: string;
  timestamp: string;
}

export interface StreamScore {
  stream: string;
  score: number;
  has_data: boolean;
  label: "REAL" | "SIMULATED" | "DEMO";
}

export interface DimensionScore {
  dimension: string;
  final_score: number;
  confidence: number;
}

export interface EvidenceConflict {
  conflict_id: string;
  dimension: string;
  description: string;
  next_validation: string;
}

export interface MarketFit {
  market_fit_score: number;
  confidence: number;
  dimensions: DimensionScore[];
  stream_scores: StreamScore[];
  conflicts: EvidenceConflict[];
  consensus: string[];
  unknowns: string[];
  best_customer: string;
  best_pricing_hypothesis: string;
  biggest_risk: string;
  recommendation: string;
  next_validation: string;
}

export interface SegmentStat {
  count: number;
  interest: number;
  willingness_to_pay: number;
  switching: number;
  top_objection: string;
}

export interface Simulation {
  participant_count: number;
  segments: Record<string, SegmentStat>;
  scenario_scores: ScenarioResult[];
  objections: string[];
  scores?: Record<string, number>;
}

export interface ScenarioResult {
  product: string;
  price: number;
  positioning: string;
  score: number;
}

export interface Opportunity {
  opportunity_id: string;
  name: string;
  fit_score: number;
  deadline: string | null;
  url: string;
  why_fit: string;
  data_label: string;
  kind: string;
}

export interface Hypothesis {
  hypothesis_id: string;
  statement: string;
  status: "SUPPORTED" | "UNCERTAIN" | "REJECTED";
  confidence: number;
  evidence_for: string[];
  evidence_against: string[];
}
