# FounderShortcut

**Your AI co-founder that validates, researches, and executes.**

Built for the Google "All Things Agentic" Hackathon — Taskmaster track.

## Problem

Founders spend weeks coordinating market research, competitor analysis, customer validation, opportunity deadlines, and startup execution tasks. Most validation advice is generic; real evidence is scattered and slow to collect.

## Solution

FounderShortcut is an autonomous AI co-founder. Give it one startup idea and it investigates the idea from multiple independent perspectives, reconciles the evidence into a Market Fit score with explicit confidence, then takes the next execution steps: strategy, pitch deck, landing page, hackathon discovery, Google Calendar scheduling, and investor outreach drafts.

## Agent Architecture (Google ADK)

Real ADK constructs drive the lifecycle (`backend/app/agents/root_agent.py`):

```
SequentialAgent("FounderShortcutRoot")
├── IdeaUnderstandingAgent          — structures the raw idea
├── MarketValidationEngine = ParallelAgent
│   ├── ResearchAgent               — cited evidence (stream A)
│   ├── SyntheticMarketAgent        — 10k persona simulation (stream B)
│   ├── CustomerDiscoveryAgent      — real candidates + outreach drafts (stream C)
│   └── VoiceValidationAgent        — consent-gated interviews (stream D)
├── MarketFitSynthesisAgent         — deterministic reconciliation + conflict detection
├── StrategyAgent                   — ICP / positioning / MVP / GTM from evidence
├── CollateralEngine = ParallelAgent(WebsiteAgent, PitchDeckAgent, MVPAgent)
├── OpportunityEngine = ParallelAgent(HackathonAgent→Calendar, InvestorAgent)
└── ReportingAgent                  — final report + "what should I do next"
```

- **ParallelAgent** runs the four validation streams concurrently.
- **Sessions/state** carry `startup_id` and stage results through the pipeline.
- Every dashboard activity maps to a persisted backend event (`events` collection).

## Synthetic Market

A MiroFish-inspired simulation:

1. A **population model** (age/location/income/AI-trust/price-sensitivity/pain distributions) is grounded in research evidence when available.
2. **10,000 personas** are sampled from those distributions (seeded, deterministic).
3. Personas are auto-segmented (early adopters, skeptics, price-sensitive, premium…).
4. **5 behavioral rounds** simulate reaction → social influence → scenario exposure → competitor comparison → final opinion, with persona memory via influence propagation.
5. A **scenario grid** (product × price × positioning) finds the best hypothesis.

Synthetic results are always labeled **SIMULATED**. They are scenario simulations for hypothesis generation — not real market demand.

## Market Fit

Four independent evidence streams are reconciled by a deterministic engine (`market_fit_service.py`) — the LLM never invents the score:

- 8 weighted dimensions with visible, configurable weights.
- Real evidence counts double vs synthetic per dimension.
- **Score ≠ confidence**: missing direct customer validation lowers confidence rather than fabricating data.
- **Evidence conflicts** are surfaced, never hidden: any dimension where sources disagree by ≥25 points produces an explanation and a next-validation action.
- Hypotheses are tracked (SUPPORTED/UNCERTAIN/REJECTED) and updated as new evidence arrives.

## Async Workflow

Cloud Run receives the request → publishes jobs to **Pub/Sub** → workers run the ADK lifecycle → all state in **Firestore** → frontend polls the live event log. Without credentials, jobs run in-process so local demos still show real orchestration.

## Google Technology

| Service | Use |
|---|---|
| Vertex AI / Gemini | Idea understanding & LLM agent reasoning |
| Google ADK | Multi-agent orchestration (LlmAgent/Sequential/Parallel/BaseAgent) |
| Cloud Run | Backend hosting |
| Firestore | Persistent startup memory |
| Pub/Sub | Async job queue |
| Google Calendar API | Auto-created deadline/prep events |

## Setup

See [docs/setup.md](docs/setup.md). Short version:

```bash
cd backend && pip install -r requirements.txt && pytest tests -q
uvicorn app.main:app --port 8080
cd frontend && npm install && npm run dev
```

## Deployment

Cloud Run instructions in [docs/deployment.md](docs/deployment.md). Firestore is the source of truth; no local filesystem persistence.

## Demo

Exact demo steps in [docs/demo.md](docs/demo.md). Demo mode (`DEMO_MODE=true`) uses cached research references, seeded personas/opportunities, controlled test customers and a simulated voice participant — while the real ADK orchestration executes. The UI labels every datum REAL / SIMULATED / DEMO.

## Safety

- Voice calls happen **only after an explicit recorded consent record**.
- Outreach messages identify themselves as automated AI research, include opt-out, and are rate-limited (5/min).
- No private-data scraping; only legitimate public sources or seeded demo contacts.
- Investor messages are drafts requiring human confirmation before sending.
- No hardcoded secrets; environment variables + Secret Manager support.

## Limitations

- Synthetic personas are simulations, not real customers. They generate hypotheses; they do not confirm demand.
- Demo-mode research uses cached reference sources, not live statistics. No figures are fabricated.
- Voice interviews in demo mode are scripted simulations with a controlled test participant.
- Seeded opportunities/investors are labeled DEMO until live discovery sources are configured.

## Tests

```bash
cd backend && python -m pytest tests -q
```

Covers persona generation determinism, price sensitivity, scenario sorting, market-fit confidence degradation without real customers, conflict detection, calendar dedup fingerprints, outreach rate limiting, the end-to-end core loop, and the full API workflow.
