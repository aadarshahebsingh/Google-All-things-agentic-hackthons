# from google.adk.agents import LlmAgent
# from google.adk.tools import google_search


# validation_agent = LlmAgent(
#     name="validation_agent",
#     model="gemini-3.6-flash",
#     tools=[google_search],
#     instruction="""
# You are a startup validation analyst.

# You will receive a raw startup idea from the user.

# Use Google Search extensively to research the startup idea.

# Research the following:

# 1. Market Size
#    - Find TAM and SAM if credible numbers are available.
#    - Prefer recent sources.
#    - Clearly identify the geography and year for each number.
#    - Do not invent market-size numbers.

# 2. Competitors
#    - Identify 2-3 direct or close competitors.
#    - Explain what each competitor does.
#    - Find their pricing if publicly available.
#    - Explain their positioning.
#    - If pricing is not publicly available, explicitly say so.

# 3. Funding Comps
#    - Find comparable startups in the same or closely related space.
#    - Look for funding rounds from the last 12-18 months where possible.
#    - Include company, round, amount, and date when available.
#    - Do not invent funding information.

# 4. Pricing Benchmarks
#    - Find pricing for similar products.
#    - Include actual prices when publicly available.
#    - Explain the pricing model (subscription, per-user, usage-based, etc.).

# Then produce a structured validation brief using exactly these sections:

# ## Summary
# Write 2-3 concise sentences describing the opportunity and market.

# ## Market Size
# Include TAM/SAM numbers where credible.
# Include source citations inline.

# ## Competitors
# For each competitor include:
# - Company
# - What they do
# - Pricing
# - Positioning
# - Source citations

# ## Funding Comps
# For each relevant funding round include:
# - Company
# - Round
# - Amount
# - Date
# - Why it is comparable
# - Source citations

# ## Pricing Benchmarks
# Include comparable products and their pricing.
# Include source citations.

# ## Top 3 weaknesses an investor would push back on
# Give exactly three specific weaknesses.
# Avoid generic statements.
# Tie each weakness directly to evidence found during research.

# IMPORTANT:
# - Use web search before answering.
# - Prefer primary sources and reputable business publications.
# - Cite specific claims and numbers inline.
# - Never fabricate numbers, competitors, funding rounds, or pricing.
# - If reliable information cannot be found, explicitly say that it could not be verified.
# """,
#     output_key="validation_brief",
# )
















from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types


class DummyValidationAgent(BaseAgent):

    async def _run_async_impl(self, ctx: InvocationContext):

        dummy_brief = """
SUMMARY
Freelancers often create invoices manually after completing work.
An app that converts Slack messages into draft invoices could reduce
administrative work for freelancers.

MARKET SIZE
The freelance economy represents a large global market.
Exact TAM/SAM figures will be added after real web research is enabled.

COMPETITORS
1. FreshBooks - freelancer accounting and invoicing software.
2. QuickBooks - accounting and invoicing platform.
3. Bonsai - freelancer-focused business management and invoicing.

FUNDING COMPS
Real funding comparisons will be added when web research is enabled.

PRICING BENCHMARKS
Comparable freelancer invoicing products commonly use subscription
pricing or free tiers with paid upgrades.

TOP 3 INVESTOR WEAKNESSES
1. Slack messages may not contain enough structured information
   to create accurate invoices automatically.
2. Existing accounting products already offer invoicing.
3. Users may be concerned about incorrect invoices being generated
   without human review.
"""

        # Store result in session state
        ctx.session.state["validation_brief"] = dummy_brief

        # ADK expects an Event, not Content
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[
                    types.Part(text=dummy_brief)
                ],
            ),
        )


validation_agent = DummyValidationAgent(
    name="validation_agent"
)