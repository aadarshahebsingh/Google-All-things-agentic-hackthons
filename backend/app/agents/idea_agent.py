"""Idea Understanding Agent (ADK LlmAgent).

Structures the founder's raw idea into hypotheses, assumptions and unknowns.
Falls back to deterministic parsing when Gemini is unavailable so the
orchestration still runs end-to-end.
"""
from __future__ import annotations

import json
import uuid

from ..models.startup import Startup
from ..services.event_service import log_event
from ..services.firestore_service import get_firestore_service

IDEA_INSTRUCTION = """
You are the Idea Understanding Agent of FounderShortcut.
Given a raw startup idea, extract structured JSON with keys:
problem, solution, industry, target_customers (list), geography,
business_model, likely_competitors (list), initial_hypotheses (list),
assumptions (list), unknowns (list).
Be specific. Do not invent market statistics.
Return ONLY valid JSON.
"""


def parse_idea_deterministic(raw_idea: str) -> dict:
    """Fallback parser used when Gemini is not configured."""
    text = raw_idea.strip().rstrip(".")
    return {
        "problem": f"Unclear how customers currently solve: {text[:120]}",
        "solution": text,
        "industry": "general",
        "target_customers": ["early adopters matching the described audience"],
        "geography": "global",
        "business_model": "subscription (hypothesis)",
        "likely_competitors": [],
        "initial_hypotheses": [
            "H1: Target customers experience this problem frequently enough to pay.",
            "H2: An AI-assisted solution is preferred over existing manual options.",
        ],
        "assumptions": ["Target segment can be reached through digital channels."],
        "unknowns": ["Willingness to pay", "Competitive intensity"],
    }


async def run_idea_agent(startup_id: str, raw_idea: str) -> Startup:
    """Run understanding via Gemini (if available) then persist to Firestore."""
    log_event(startup_id, "IdeaUnderstandingAgent", "Understanding startup idea")
    parsed = None
    try:
        from google.adk.runners import InMemoryRunner  # type: ignore
        from google.adk.agents import LlmAgent  # type: ignore
        from google.genai import types  # type: ignore

        agent = LlmAgent(name="IdeaUnderstandingAgent", model=_model_name(),
                         instruction=IDEA_INSTRUCTION)
        runner = InMemoryRunner(agent=agent, app_name="founder-shortcut")
        content = types.Content(role="user", parts=[types.Part(text=raw_idea)])
        result_text = ""
        async for event in runner.run_async(user_id="founder", session_id=startup_id,
                                            new_message=content):
            if event.content and event.content.parts:
                result_text += event.content.parts[0].text or ""
        # strip markdown fences if present
        cleaned = result_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        parsed = json.loads(cleaned)
        log_event(startup_id, "IdeaUnderstandingAgent", "Structured via Gemini")
    except Exception as exc:
        log_event(startup_id, "IdeaUnderstandingAgent",
                  f"Gemini unavailable ({type(exc).__name__}); using deterministic parser", level="WARN")

    if not parsed:
        parsed = parse_idea_deterministic(raw_idea)

    startup = Startup(
        startup_id=startup_id,
        raw_idea=raw_idea,
        status="RUNNING",
        **{k: v for k, v in parsed.items() if k in Startup.model_fields},
    )
    get_firestore_service().set("startups", startup_id, startup.model_dump())
    log_event(startup_id, "IdeaUnderstandingAgent", "Startup profile saved to Firestore")
    return startup


def _model_name() -> str:
    from ..config.settings import get_settings

    return get_settings().gemini_model


def new_startup_id() -> str:
    return uuid.uuid4().hex[:12]
