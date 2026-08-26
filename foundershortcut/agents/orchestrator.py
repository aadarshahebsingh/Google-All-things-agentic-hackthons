from google.adk.agents import SequentialAgent, ParallelAgent

from agents.validation_agent import validation_agent
from agents.deck_agent import deck_agent
from agents.website_agent import website_agent

collateral_agent = ParallelAgent(
    name="collateral_agent",
    sub_agents=[
        deck_agent,
        website_agent,
    ],
)

orchestrator = SequentialAgent(
    name="founder_shortcut_orchestrator",
    sub_agents=[
        validation_agent,
        collateral_agent,
    ],
)