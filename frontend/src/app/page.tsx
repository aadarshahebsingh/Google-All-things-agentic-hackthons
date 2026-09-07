"use client";

import { useEffect, useState } from "react";
import {
  getActivity, getAssets, getHypotheses, getMarketFit,
  getOpportunities, getSimulation, getStartup, grantConsentAndInterview,
  startValidation, testScenario,
} from "@/lib/api";
import type { AgentEvent, Hypothesis, MarketFit, Opportunity, Simulation } from "@/types";

const DEMO_IDEA =
  "I want to build an AI platform that helps engineering students find relevant internships.";

type StageState = "WAITING" | "RUNNING" | "COMPLETE" | "WAITING_FOR_CONSENT";

export default function Dashboard() {
  const [idea, setIdea] = useState(DEMO_IDEA);
  const [startupId, setStartupId] = useState<string | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [fit, setFit] = useState<MarketFit | null>(null);
  const [sim, setSim] = useState<Simulation | null>(null);
  const [opps, setOpps] = useState<Opportunity[]>([]);
  const [hyps, setHyps] = useState<Hypothesis[]>([]);
  const [assets, setAssets] = useState<Record<string, unknown> | null>(null);
  const [customers, setCustomers] = useState<{ candidate_id: string; customer_type: string }[]>([]);
  const [running, setRunning] = useState(false);
  const [scenarioResult, setScenarioResult] = useState<string>("");

  // Poll live agent activity
  useEffect(() => {
    if (!startupId) return;
    const t = setInterval(async () => {
      const a = await getActivity(startupId);
      setEvents(a.events);
      const s = await getStartup(startupId);
      if (s.status === "COMPLETE") {
        clearInterval(t);
        setRunning(false);
        loadAll(startupId);
      }
    }, 2000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startupId]);

  async function loadAll(id: string) {
    setFit(await getMarketFit(id));
    setSim(await getSimulation(id));
    setOpps((await getOpportunities(id)).opportunities);
    setHyps((await getHypotheses(id)).hypotheses);
    setAssets(await getAssets(id));
    const c = await fetch(`/api/startup/${id}/customers`).then((r) => r.json());
    setCustomers(c.candidates || []);
  }

  async function handleValidate() {
    setRunning(true);
    setEvents([]); setFit(null); setSim(null); setOpps([]); setHyps([]); setAssets(null);
    const res = await startValidation(idea);
    setStartupId(res.startup_id);
  }

  async function handleConsent(candidateId: string) {
    if (!startupId) return;
    await grantConsentAndInterview(startupId, candidateId);
    await loadAll(startupId);
  }

  async function runScenario(price: number) {
    if (!startupId) return;
    const r = await testScenario(startupId, price, "save time");
    setScenarioResult(`₹${price} → score ${r.score} (${r.label})`);
  }

  const stageState = (agent: string): StageState => {
    const relevant = events.filter((e) => e.agent.startsWith(agent));
    if (!relevant.length) return running ? "RUNNING" : "WAITING";
    return "COMPLETE";
  };

  return (
    <div className="container">
      <h1>FounderShortcut</h1>
      <p className="muted" style={{ marginBottom: 20 }}>
        Your AI co-founder that validates, researches, and executes.
      </p>

      <div className="card">
        <textarea rows={3} value={idea} onChange={(e) => setIdea(e.target.value)} />
        <div style={{ marginTop: 12 }}>
          <button onClick={handleValidate} disabled={running}>
            {running ? "Agents working…" : "Validate My Idea"}
          </button>
          <span className="badge DEMO" style={{ marginLeft: 12 }}>Demo mode</span>
        </div>
      </div>

      {startupId && (
        <>
          <div className="card">
            <h2>Live Agent Activity</h2>
            {["ResearchAgent", "SyntheticMarketAgent", "CustomerDiscoveryAgent",
              "VoiceValidationAgent", "MarketFitAgent", "StrategyAgent"].map((a) => (
                <p key={a}>
                  <strong>{a}</strong>:{" "}
                  <span className="muted">{stageState(a)}</span>
                </p>
              ))}
            <div style={{ maxHeight: 320, overflowY: "auto", marginTop: 12 }}>
              {[...events].reverse().map((e) => (
                <div key={e.event_id} className={`event ${e.level}`}>
                  <time>{new Date(e.timestamp).toLocaleTimeString()}</time>
                  <span className="agent">{e.agent}</span>
                  <span>{e.message}</span>
                </div>
              ))}
            </div>
          </div>

          {fit && fit.market_fit_score > 0 && (
            <div className="grid cols2">
              <div className="card">
                <h2>Market Fit</h2>
                <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
                  <div>
                    <span className="score-big">{fit.market_fit_score.toFixed(0)}</span>
                    <span className="muted"> / 100</span>
                  </div>
                  <div>
                    <div className="muted">Confidence</div>
                    <strong>{fit.confidence?.toFixed(0)}%</strong>
                  </div>
                </div>
                {fit.dimensions.map((d) => (
                  <div key={d.dimension} style={{ margin: "8px 0" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: ".85rem" }}>
                      <span>{d.dimension.replace("_", " ")}</span><span>{d.final_score}</span>
                    </div>
                    <div className="bar"><div style={{ width: `${d.final_score}%` }} /></div>
                  </div>
                ))}
              </div>

              <div>
                <div className="card">
                  <h2>Evidence Streams</h2>
                  {fit.stream_scores.map((s) => (
                    <p key={s.stream} style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ textTransform: "uppercase" }}>{s.stream}</span>
                      <span>
                        {s.has_data ? s.score.toFixed(0) : "no data"}{" "}
                        <span className={`badge ${s.label}`}>{s.label}</span>
                      </span>
                    </p>
                  ))}
                  <p className="muted" style={{ marginTop: 8 }}>{fit.biggest_risk}</p>
                  <p style={{ marginTop: 8 }}>✅ {fit.recommendation}</p>
                  <p className="muted" style={{ marginTop: 8 }}>
                    Next validation: {fit.next_validation}
                  </p>
                </div>

                {fit.conflicts.length > 0 && (
                  <div className="card">
                    <h2>⚠️ Evidence Conflicts</h2>
                    {fit.conflicts.slice(0, 3).map((c) => (
                      <p key={c.conflict_id}>• {c.description}</p>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {sim && sim.participant_count && (
            <div className="grid cols2">
              <div className="card">
                <h2>Synthetic Market <span className="badge SIMULATED">SIMULATED</span></h2>
                <p>{sim.participant_count.toLocaleString()} synthetic market participants</p>
                <table style={{ marginTop: 12 }}>
                  <thead><tr><th>Segment</th><th>Interest</th><th>WTP</th><th>Top objection</th></tr></thead>
                  <tbody>
                    {Object.entries(sim.segments || {}).slice(0, 8).map(([seg, st]) => (
                      <tr key={seg}>
                        <td>{seg.replace("_", " ")}</td>
                        <td>{(st.interest * 100).toFixed(0)}%</td>
                        <td>{(st.willingness_to_pay * 100).toFixed(0)}%</td>
                        <td className="muted">{st.top_objection || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="card">
                <h2>Scenario Testing</h2>
                {(sim.scenario_scores || []).slice(0, 5).map((s, i) => (
                  <p key={i}>₹{s.price} · {s.positioning} → <strong>{s.score}</strong></p>
                ))}
                <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
                  {[49, 99, 199].map((p) => (
                    <button key={p} onClick={() => runScenario(p)}>Test ₹{p}</button>
                  ))}
                </div>
                {scenarioResult && <p className="muted" style={{ marginTop: 8 }}>{scenarioResult}</p>}
              </div>
            </div>
          )}

          {customers.length > 0 && (
            <div className="card">
              <h2>Customer Validation</h2>
              {customers.map((c) => (
                <p key={c.candidate_id} style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>{c.customer_type}</span>
                  <button onClick={() => handleConsent(c.candidate_id)}>
                    Grant consent & interview
                  </button>
                </p>
              ))}
            </div>
          )}

          {hypsWithData(hyps) && (
            <div className="card">
              <h2>Hypotheses</h2>
              {hyps.map((h) => (
                <p key={h.hypothesis_id}>
                  <strong>{h.status}</strong> ({h.confidence}%) — {h.statement}
                </p>
              ))}
            </div>
          )}

          {opps.length > 0 && (
            <div className="card">
              <h2>Opportunities & Calendar</h2>
              {opps.map((o) => (
                <p key={o.opportunity_id}>
                  🎯 <strong>{o.name}</strong> — fit {o.fit_score}, deadline {o.deadline}{" "}
                  <span className={`badge ${o.data_label}`}>{o.data_label}</span>{" "}
                  {o.url && <a href={o.url} target="_blank" className="muted">link</a>}
                </p>
              ))}
              <p className="muted">Preparation events were scheduled automatically (see activity log).</p>
            </div>
          )}

          {assets && assets.deck && (assets.deck as { slides?: unknown[] }).slides && (
            <div className="card">
              <h2>Generated Assets</h2>
              <p>✅ Pitch deck ({(assets.deck as { slides: unknown[] }).slides.length} slides)</p>
              <p>✅ Landing page content generated</p>
              <p>✅ MVP plan</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function hypsWithData(hyps: Hypothesis[]) {
  return hyps && hyps.length > 0;
}
