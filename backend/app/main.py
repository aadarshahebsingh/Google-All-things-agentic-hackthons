"""FounderShortcut FastAPI application.

Async architecture: POST /api/start-validation creates the startup record and
runs the ADK root agent as a background task (in-process fallback) or via
Pub/Sub when configured. The frontend polls /activity and resource endpoints.
"""
from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .agents.idea_agent import new_startup_id, parse_idea_deterministic
from .config.settings import get_settings
from .services.event_service import get_events, log_event
from .services.firestore_service import get_firestore_service
from .services.pubsub_service import get_pubsub_service

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_event("system", "System", f"FounderShortcut API starting (demo_mode={settings.demo_mode}, "
                                 f"store={get_firestore_service().backend}, "
                                 f"jobs={get_pubsub_service().backend})")
    yield


app = FastAPI(title="FounderShortcut API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Request/response models -----------------------------------------------

class IdeaRequest(BaseModel):
    idea: str


class ConsentRequest(BaseModel):
    startup_id: str
    candidate_id: str


class ScenarioRequest(BaseModel):
    startup_id: str
    product: str | None = None
    price: float = 99.0
    positioning: str = "save time"


# ---- Workflow runner ---------------------------------------------------------

def run_workflow(startup_id: str, raw_idea: str) -> None:
    """Run the ADK root agent lifecycle. Falls back to direct stage execution
    if the ADK runner cannot start (e.g. no model credentials in demo)."""
    fs = get_firestore_service()
    try:
        from google.adk.runners import InMemoryRunner  # type: ignore
        from google.genai import types  # type: ignore

        from .agents.root_agent import root_agent

        runner = InMemoryRunner(agent=root_agent, app_name="founder-shortcut")
        # Seed state; stages populate results.
        session = asyncio.get_event_loop().run_until_complete(
            runner.session_service.create_session(app_name="founder-shortcut",
                                                  user_id="founder",
                                                  state={"startup_id": startup_id,
                                                         "raw_idea": raw_idea}))
        content = types.Content(role="user", parts=[types.Part(text=raw_idea)])
        asyncio.get_event_loop().run_until_complete(
            _drain(runner.run_async(user_id="founder", session_id=session.id,
                                    new_message=content)))
    except Exception as exc:
        log_event(startup_id, "Orchestrator",
                  f"ADK runner unavailable ({type(exc).__name__}: {exc}); executing pipeline directly",
                  level="WARN")
        _run_pipeline_direct(startup_id, raw_idea)


async def _drain(agen):
    async for _ in agen:
        pass


def _run_pipeline_direct(startup_id: str, raw_idea: str) -> None:
    """Deterministic stage-by-stage execution (same agents, explicit order).
    Used only when the ADK runner can't be initialized."""
    from .agents.collateral_agents import run_deck_agent, run_mvp_agent, run_website_agent
    from .agents.customer_discovery_agent import run_customer_discovery_agent
    from .agents.market_fit_agent import run_market_fit_agent
    from .agents.opportunity_agents import run_hackathon_agent, run_investor_agent
    from .agents.research_agent import run_research_agent
    from .agents.strategy_agent import run_strategy_agent
    from .agents.synthetic_market_agent import run_synthetic_market_agent
    from .agents.voice_validation_agent import has_consent

    fs = get_firestore_service()
    startup = dict(fs.get("startups", startup_id) or {})
    parsed = parse_idea_deterministic(raw_idea)
    startup.update(parsed)
    fs.set("startups", startup_id, startup)
    log_event(startup_id, "IdeaUnderstandingAgent", "Startup profile structured")

    research = run_research_agent(startup_id, parsed["solution"])

    def synth():
        return run_synthetic_market_agent(startup_id, startup, research)

    def discovery():
        return run_customer_discovery_agent(startup_id, startup)

    def voice():
        candidates = fs.list("customers", "startup_id", startup_id)
        for c in candidates[:1]:
            if has_consent(startup_id, c["candidate_id"]):
                from .agents.voice_validation_agent import run_voice_interview

                return run_voice_interview(startup_id, c["candidate_id"], parsed["initial_hypotheses"])
        log_event(startup_id, "VoiceValidationAgent", "WAITING_FOR_CONSENT")
        return {"status": "WAITING_FOR_CONSENT"}

    # Parallel streams (research already done above for population grounding).
    synthetic, customer = synth(), discovery()

    run_market_fit_agent(startup_id)
    run_strategy_agent(startup_id)
    run_website_agent(startup_id); run_deck_agent(startup_id); run_mvp_agent(startup_id)
    run_hackathon_agent(startup_id); run_investor_agent(startup_id)
    fit = fs.get("market_fit", startup_id) or {}
    fs.update("startups", startup_id, {"status": "COMPLETE"})
    log_event(startup_id, "ReportingAgent", f"Workflow complete: Market Fit {fit.get('market_fit_score')}/100")


# ---- Endpoints ----------------------------------------------------------------

@app.post("/api/startup")
def create_startup(req: IdeaRequest):
    startup_id = new_startup_id()
    parsed = parse_idea_deterministic(req.idea)
    record = {"startup_id": startup_id, "raw_idea": req.idea,
              "status": "CREATED", **parsed}
    get_firestore_service().set("startups", startup_id, record)
    log_event(startup_id, "Orchestrator", "Started validation")
    return record


@app.post("/api/start-validation")
def start_validation(req: IdeaRequest):
    startup = create_startup(req)
    sid = startup["startup_id"]
    published = get_pubsub_service().publish_job("full_validation", {"startup_id": sid})
    if not published:
        # In-process background execution (local/demo fallback)
        loop = asyncio.new_event_loop()
        import threading

        t = threading.Thread(target=lambda: loop.run_until_complete(
            asyncio.to_thread(run_workflow, sid, req.idea)), daemon=True)
        t.start()
    return {"startup_id": sid, "status": "RUNNING",
            "job_backend": "pubsub" if published else "in-process"}


@app.get("/api/startup/{startup_id}")
def get_startup(startup_id: str):
    rec = get_firestore_service().get("startups", startup_id)
    return rec or {"error": "not_found"}


@app.get("/api/startup/{startup_id}/activity")
def activity(startup_id: str):
    return {"events": get_events(startup_id),
            "backend": get_firestore_service().backend}


@app.get("/api/startup/{startup_id}/research")
def research(startup_id: str):
    return get_firestore_service().get("research", startup_id) or {}


@app.get("/api/startup/{startup_id}/personas")
def personas(startup_id: str):
    meta = get_firestore_service().get("personas_meta", startup_id) or {}
    sim = get_firestore_service().get("simulations", startup_id) or {}
    return {"population_model": meta.get("population_model"),
            "grounded_in_research": meta.get("grounded_in_research"),
            "participant_count": sim.get("participant_count"),
            "segments": sim.get("segments")}


@app.get("/api/startup/{startup_id}/simulation")
def simulation(startup_id: str):
    return get_firestore_service().get("simulations", startup_id) or {}


@app.get("/api/startup/{startup_id}/market-fit")
def market_fit(startup_id: str):
    return get_firestore_service().get("market_fit", startup_id) or {}


@app.get("/api/startup/{startup_id}/hypotheses")
def hypotheses(startup_id: str):
    return {"hypotheses": get_firestore_service().list("hypotheses", "startup_id", startup_id)}


@app.get("/api/startup/{startup_id}/customers")
def customers(startup_id: str):
    return {"candidates": get_firestore_service().list("customers", "startup_id", startup_id)}


@app.get("/api/startup/{startup_id}/interviews")
def interviews(startup_id: str):
    return {"interviews": get_firestore_service().list("interviews", "startup_id", startup_id)}


@app.post("/api/consent")
def consent(req: ConsentRequest):
    from .agents.voice_validation_agent import grant_consent, run_voice_interview

    c = grant_consent(req.startup_id, req.candidate_id)
    result = run_voice_interview(req.startup_id, req.candidate_id)
    return {"consent": c.model_dump(), "interview": result}


@app.get("/api/startup/{startup_id}/opportunities")
def opportunities(startup_id: str):
    return {"opportunities": get_firestore_service().list("hackathons", "startup_id", startup_id)}


@app.get("/api/startup/{startup_id}/calendar")
def calendar_view(startup_id: str):
    events = get_events(startup_id)
    cal = [e for e in events if e.get("agent") == "CalendarAgent"]
    return {"calendar_log": cal,
            "note": "Event creation status comes from the CalendarAgent audit log."}


@app.get("/api/startup/{startup_id}/assets")
def assets(startup_id: str):
    fs = get_firestore_service()
    return {
        "website": fs.get("assets_website", startup_id) or {},
        "deck": fs.get("assets_deck", startup_id) or {},
        "mvp": fs.get("assets_mvp", startup_id) or {},
        "report": fs.get("market_fit", startup_id) or {},
    }


@app.post("/api/scenario")
def scenario(req: ScenarioRequest):
    """Run an on-demand what-if scenario against stored personas metadata."""
    fs = get_firestore_service()
    sim = fs.get("simulations", req.startup_id) or {}
    base = ((sim.get("scores") or {}).get("best_scenario") or {})
    product = req.product or base.get("product") or "the product"
    # Lightweight re-scoring using stored segment data.
    segs = sim.get("segments") or {}
    mean_interest = sum(s["interest"] for s in segs.values()) / max(len(segs), 1)
    adj = {0.0: 0.05, 49.0: 0.03, 99.0: 0.0, 199.0: -0.04, 499.0: -0.10}.get(req.price, -0.05)
    score = max(0.0, min(100.0, (mean_interest + adj) * 100))
    result = {"scenario_id": uuid.uuid4().hex[:8], "product": product, "price": req.price,
              "positioning": req.positioning, "score": round(score, 1), "label": "SIMULATED"}
    log_event(req.startup_id, "ScenarioEngine",
              f"On-demand scenario: ₹{req.price} {req.positioning} → {result['score']}")
    return result


@app.get("/api/health")
def health():
    return {"status": "ok", "demo_mode": settings.demo_mode,
            "store_backend": get_firestore_service().backend,
            "job_backend": get_pubsub_service().backend}
