"""Root ADK orchestration.

Architecture (real Google ADK constructs):

  root_agent = SequentialAgent(
    IdeaUnderstandingAgent (LlmAgent-backed function agent)
    MarketValidationEngine = ParallelAgent(
        ResearchAgent, SyntheticMarketAgent,
        CustomerDiscoveryAgent, VoiceValidationAgent)
    MarketFitSynthesisAgent
    StrategyAgent
    CollateralEngine = ParallelAgent(Website, PitchDeck, MVP)
    OpportunityEngine = ParallelAgent(Hackathon+Calendar, Investor)
    ReportingAgent
  )

Each stage is implemented as an ADK BaseAgent subclass so the ADK runner
drives the whole lifecycle; heavy work lives in the per-agent modules.
"""
from __future__ import annotations

import asyncio
import logging

from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent, SequentialAgent  # type: ignore
from google.adk.agents.invocation_context import InvocationContext  # type: ignore
from google.adk.events import Event  # type: ignore
from google.adk.events import Event  # type: ignore

from ..services.event_service import log_event
from ..services.firestore_service import get_firestore_service

log = logging.getLogger(__name__)


class FounderShortcutAgent(BaseAgent):
    """Base for all pipeline stages: async run via ADK invocation context."""

    stage_name: str

    async def _run_async_impl(self, ctx: InvocationContext):
        startup_id = ctx.session.state.get("startup_id", "")
        try:
            result = await asyncio.to_thread(self._execute, startup_id, dict(ctx.session.state))
            ctx.session.state[f"{self.stage_name}_result"] = _safe(result)
            yield Event(author=self.name, content=None)
        except Exception as exc:  # partial failure must not destroy the workflow
            log.exception("Stage %s failed", self.stage_name)
            log_event(startup_id, self.stage_name, f"Failed: {exc}", level="ERROR")
            ctx.session.state[f"{self.stage_name}_error"] = str(exc)
            yield Event(author=self.name, content=None)

    def _execute(self, startup_id: str, state: dict) -> dict:
        raise NotImplementedError

# ---- Stage implementations -------------------------------------------------

class IdeaStage(FounderShortcutAgent):
    stage_name: str = "idea"

    def _execute(self, startup_id: str, state: dict) -> dict:
        from .idea_agent import parse_idea_deterministic

        parsed = parse_idea_deterministic(state.get("raw_idea", ""))
        fs = get_firestore_service()
        fs.update("startups", startup_id, parsed)
        return parsed


class ResearchStage(FounderShortcutAgent):
    stage_name: str = "research"

    def _execute(self, startup_id: str, state: dict) -> dict:
        from .research_agent import run_research_agent

        return run_research_agent(startup_id, state.get("solution") or state.get("raw_idea", ""))


class SyntheticMarketStage(FounderShortcutAgent):
    stage_name: str = "synthetic_market"

    def _execute(self, startup_id: str, state: dict) -> dict:
        from .synthetic_market_agent import run_synthetic_market_agent

        return run_synthetic_market_agent(startup_id, state,
                                          state.get("research_result"))


class CustomerDiscoveryStage(FounderShortcutAgent):
    stage_name: str = "customer_discovery"

    def _execute(self, startup_id: str, state: dict) -> dict:
        from .customer_discovery_agent import run_customer_discovery_agent

        return run_customer_discovery_agent(startup_id, state)


class VoiceValidationStage(FounderShortcutAgent):
    stage_name: str = "voice_validation"

    def _execute(self, startup_id: str, state: dict) -> dict:
        # Consent-gated: without consent this stage records WAITING and moves on.
        from .voice_validation_agent import has_consent

        candidates = get_firestore_service().list("customers", "startup_id", startup_id)
        interviewed = []
        for c in candidates[:1]:
            if has_consent(startup_id, c["candidate_id"]):
                from .voice_validation_agent import run_voice_interview

                interviewed.append(run_voice_interview(startup_id, c["candidate_id"],
                                                       state.get("initial_hypotheses")))
        if not interviewed:
            log_event(startup_id, "VoiceValidationAgent", "WAITING_FOR_CONSENT")
            return {"status": "WAITING_FOR_CONSENT"}
        return {"interviews": interviewed}


class MarketFitStage(FounderShortcutAgent):
    stage_name: str = "market_fit"

    def _execute(self, startup_id: str, state: dict) -> dict:
        from .market_fit_agent import run_market_fit_agent

        return run_market_fit_agent(startup_id)


class StrategyStage(FounderShortcutAgent):
    stage_name: str = "strategy"

    def _execute(self, startup_id: str, state: dict) -> dict:
        from .strategy_agent import run_strategy_agent

        return run_strategy_agent(startup_id)


class WebsiteStage(FounderShortcutAgent):
    stage_name: str = "website"

    def _execute(self, startup_id: str, state: dict) -> dict:
        from .collateral_agents import run_website_agent

        return run_website_agent(startup_id)


class DeckStage(FounderShortcutAgent):
    stage_name: str = "deck"

    def _execute(self, startup_id: str, state: dict) -> dict:
        from .collateral_agents import run_deck_agent

        return run_deck_agent(startup_id)


class MVPStage(FounderShortcutAgent):
    stage_name: str = "mvp"

    def _execute(self, startup_id: str, state: dict) -> dict:
        from .collateral_agents import run_mvp_agent

        return run_mvp_agent(startup_id)


class HackathonStage(FounderShortcutAgent):
    stage_name: str = "hackathon"

    def _execute(self, startup_id: str, state: dict) -> dict:
        from .opportunity_agents import run_hackathon_agent

        return {"opportunities": run_hackathon_agent(startup_id)}


class InvestorStage(FounderShortcutAgent):
    stage_name: str = "investor"

    def _execute(self, startup_id: str, state: dict) -> dict:
        from .opportunity_agents import run_investor_agent

        return {"drafts": run_investor_agent(startup_id)}


class ReportingStage(FounderShortcutAgent):
    stage_name: str = "reporting"

    def _execute(self, startup_id: str, state: dict) -> dict:
        fs = get_firestore_service()
        fit = fs.get("market_fit", startup_id) or {}
        fs.update("startups", startup_id, {"status": "COMPLETE"})
        log_event(startup_id, "ReportingAgent",
                  f"Workflow complete. Market Fit {fit.get('market_fit_score', 'N/A')}/100")
        return {"market_fit_score": fit.get("market_fit_score"),
                "confidence": fit.get("confidence"),
                "next_actions": _top_actions(fs, startup_id, fit)}

    def _top_actions(self, fs, startup_id: str, fit: dict) -> list[dict]:
        actions = []
        conflicts = fit.get("conflicts", [])
        if conflicts:
            actions.append({"action": conflicts[0]["next_validation"], "why": conflicts[0]["description"]})
        opps = fs.list("hackathons", "startup_id", startup_id)
        if opps:
            actions.append({"action": f"Prepare submission: {opps[0]['name']}",
                            "why": f"Deadline {opps[0].get('deadline')}, fit {opps[0].get('fit_score')}/100"})
        actions.append({"action": "Interview 5 more real customers",
                        "why": "Direct validation raises confidence fastest."})
        return actions[:3]


def _safe(obj) -> dict:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return {"value": str(obj)}


# ---- Assemble the ADK tree -------------------------------------------------

market_validation_engine = ParallelAgent(
    name="MarketValidationEngine",
    sub_agents=[
        ResearchStage(name="ResearchAgent", description="Real-world research evidence"),
        SyntheticMarketStage(name="SyntheticMarketAgent", description="Persona simulation"),
        CustomerDiscoveryStage(name="CustomerDiscoveryAgent", description="Find real customers"),
        VoiceValidationStage(name="VoiceValidationAgent", description="Consent-gated voice interviews"),
    ],
)

collateral_engine = ParallelAgent(
    name="CollateralEngine",
    sub_agents=[
        WebsiteStage(name="WebsiteAgent"),
        DeckStage(name="PitchDeckAgent"),
        MVPStage(name="MVPAgent"),
    ],
)

opportunity_engine = ParallelAgent(
    name="OpportunityEngine",
    sub_agents=[
        HackathonStage(name="HackathonAgent"),
        InvestorStage(name="InvestorAgent"),
    ],
)

root_agent = SequentialAgent(
    name="FounderShortcutRoot",
    description="Autonomous AI co-founder lifecycle",
    sub_agents=[
        IdeaStage(name="IdeaUnderstandingAgent"),
        market_validation_engine,
        MarketFitStage(name="MarketFitSynthesisAgent"),
        StrategyStage(name="StrategyAgent"),
        collateral_engine,
        opportunity_engine,
        ReportingStage(name="ReportingAgent"),
    ],
)
