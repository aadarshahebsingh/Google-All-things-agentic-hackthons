# Architecture

## Overview

FounderShortcut is an autonomous AI co-founder built on Google ADK. A founder submits a startup idea; a multi-agent pipeline researches the market, simulates a synthetic market of 10,000 AI personas, discovers real customer candidates, conducts consent-gated voice interviews, reconciles all evidence into a deterministic Market Fit score, and then executes: strategy, collateral, opportunities and calendar scheduling.

## Agent Tree (Google ADK)

```
root_agent = SequentialAgent("FounderShortcutRoot")
├── IdeaUnderstandingAgent          (BaseAgent stage; LlmAgent-backed when Gemini configured)
├── MarketValidationEngine          = ParallelAgent
│   ├── ResearchAgent               — cited evidence (stream A: REAL)
│   ├── SyntheticMarketAgent        — persona simulation (stream B: SIMULATED)
│   ├── CustomerDiscoveryAgent      — real candidates (stream C: REAL)
│   └── VoiceValidationAgent        — consent-gated interviews (stream D: REAL)
├── MarketFitSynthesisAgent         — deterministic reconciliation
├── StrategyAgent                   — ICP / positioning / MVP / GTM from evidence
├── CollateralEngine                = ParallelAgent(Website, PitchDeck, MVP)
├── OpportunityEngine               = ParallelAgent(Hackathon+Calendar, Investor)
└── ReportingAgent                  — final report + top-3 next actions
```

All stages are `google.adk.agents.BaseAgent` subclasses driven by the ADK runner. When Gemini/ADK runtime is unavailable (local demo), the same agent modules execute through an explicit fallback pipeline (`_run_pipeline_direct`) so orchestration is never faked in the UI — the fallback is announced in the event log.

## Four Independent Evidence Streams

Streams A–D run **in parallel** and do not depend on each other:

- Research never depends on personas.
- Personas never depend on real calls.
- Outreach never depends on personas.
- The Market Fit report is produced even with zero completed interviews — confidence drops instead.

## Market Fit Engine

- 8 weighted dimensions (weights visible/configurable in `market_fit_service.DEFAULT_WEIGHTS`).
- Real evidence counts double vs synthetic per dimension.
- Score ≠ Confidence: missing direct validation lowers confidence, not fabricated data.
- Conflict detection flags any dimension where sources disagree by ≥25 points.

## Async Workflow

Cloud Run → Pub/Sub topic (`founder-shortcut-jobs`) → worker executes ADK lifecycle → results written to Firestore → frontend polls `/activity` for live events. Without Pub/Sub credentials, jobs run in-process via background threads (clearly labeled in logs).

## Data

Firestore collections: startups, evidence, personas_meta, simulations, customers, outreach, consents, interviews, hypotheses, market_fit, strategy, hackathons, investors, events. In-memory fallback store used only when Firestore is unavailable.
