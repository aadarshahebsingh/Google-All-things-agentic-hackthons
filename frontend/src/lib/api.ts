import { AgentEvent, Hypothesis, MarketFit, Opportunity, Simulation } from "@/types";

export const API = "/api";

export async function startValidation(idea: string): Promise<{ startup_id: string }> {
  const r = await fetch(`${API}/start-validation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ idea }),
  });
  return r.json();
}

export async function getStartup(id: string) {
  const r = await fetch(`${API}/startup/${id}`);
  return r.json();
}

export async function getActivity(id: string): Promise<{ events: AgentEvent[] }> {
  const r = await fetch(`${API}/startup/${id}/activity`);
  return r.json();
}

export async function getMarketFit(id: string): Promise<MarketFit> {
  const r = await fetch(`${API}/startup/${id}/market-fit`);
  return r.json();
}

export async function getSimulation(id: string): Promise<Simulation> {
  const r = await fetch(`${API}/startup/${id}/simulation`);
  return r.json();
}

export async function getOpportunities(id: string): Promise<{ opportunities: Opportunity[] }> {
  const r = await fetch(`${API}/startup/${id}/opportunities`);
  return r.json();
}

export async function getHypotheses(id: string): Promise<{ hypotheses: Hypothesis[] }> {
  const r = await fetch(`${API}/startup/${id}/hypotheses`);
  return r.json();
}

export async function getAssets(id: string) {
  const r = await fetch(`${API}/startup/${id}/assets`);
  return r.json();
}

export async function grantConsentAndInterview(startupId: string, candidateId: string) {
  const r = await fetch(`${API}/consent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ startup_id: startupId, candidate_id: candidateId }),
  });
  return r.json();
}

export async function testScenario(startupId: string, price: number, positioning: string) {
  const r = await fetch(`${API}/scenario`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ startup_id: startupId, price, positioning }),
  });
  return r.json();
}
