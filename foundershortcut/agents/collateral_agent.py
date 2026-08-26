from google.adk.agents import ParallelAgent

from .deck_agent import deck_agent
from .website_agent import website_agent


collateral_agent = ParallelAgent(
    name="collateral_agent",
    sub_agents=[
        deck_agent,
        website_agent,
    ],
)