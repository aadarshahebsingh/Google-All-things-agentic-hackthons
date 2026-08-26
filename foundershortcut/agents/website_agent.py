from google.adk.agents import LlmAgent


website_agent = LlmAgent(
    name="website_agent",
    model="gemini-2.5-flash",
    instruction="""
Using the validation brief below, generate a single-file HTML landing page
for this startup.

The page should include:

- A compelling hero section
- Problem section
- Solution section
- Key benefits
- Market/context section
- Social proof or credibility section if supported by the brief
- Waitlist email capture form
- Clear CTA
- Responsive CSS
- Modern professional startup design

Validation brief:

{validation_brief}

Output only the raw HTML.
Do not use markdown code fences.
Do not output explanations outside the HTML.
Do not invent statistics or claims that are not supported by the validation brief.
""",
    output_key="website_html",
)