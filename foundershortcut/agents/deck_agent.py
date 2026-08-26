from google.adk.agents import LlmAgent

deck_agent = LlmAgent(
    name="deck_agent",
    model="gemini-3.6-flash",
    instruction="""
Using the validation brief below, generate pitch deck content as JSON.

Validation brief:
{validation_brief}

Output JSON with this shape:

{
  "slides": [
    {
      "title": "...",
      "bullets": ["...", "..."]
    }
  ]
}

Include these slides:
- Problem
- Solution
- Market Size
- Competitors
- Business Model
- Ask

Ground every claim in the validation brief.
Do not invent numbers.
Return only valid JSON.
""",
    output_key="deck_content",
)