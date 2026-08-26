import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from tools.deck_builder import build_deck

# --------------------------------------------------
# Load .env
# --------------------------------------------------

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path, override=True)

print(
    "GOOGLE_API_KEY loaded:",
    bool(os.getenv("GOOGLE_API_KEY"))
)


# --------------------------------------------------
# ADK imports
# --------------------------------------------------

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.orchestrator import orchestrator


async def main():

    # --------------------------------------------------
    # Session setup
    # --------------------------------------------------

    session_service = InMemorySessionService()

    app_name = "founder_shortcut"
    user_id = "user_1"
    session_id = "session_1"

    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )


    # --------------------------------------------------
    # Runner
    # --------------------------------------------------

    runner = Runner(
        agent=orchestrator,
        app_name=app_name,
        session_service=session_service,
    )


    # --------------------------------------------------
    # Startup idea
    # --------------------------------------------------

    startup_idea = """
An app that helps freelancers auto-generate invoices
from Slack messages.
"""


    content = types.Content(
        role="user",
        parts=[
            types.Part(
                text=startup_idea
            )
        ],
    )


    # --------------------------------------------------
    # Display startup idea
    # --------------------------------------------------

    print("\n" + "=" * 80)
    print("STARTUP IDEA")
    print("=" * 80)

    print(startup_idea.strip())


    # --------------------------------------------------
    # Run agents
    # --------------------------------------------------

    print("\n" + "=" * 80)
    print("RUNNING AGENTS...")
    print("=" * 80)


    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    ):

        if event.is_final_response():

            if event.content and event.content.parts:

                for part in event.content.parts:

                    if part.text:
                        print("\n" + part.text)


    # --------------------------------------------------
    # Retrieve updated session
    # --------------------------------------------------

    updated_session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )


    # --------------------------------------------------
    # Get outputs from session state
    # --------------------------------------------------

    validation_brief = updated_session.state.get(
        "validation_brief"
    )

    deck_content = updated_session.state.get(
        "deck_content"
    )

    website_html = updated_session.state.get(
        "website_html"
    )


    # --------------------------------------------------
    # Validation Brief
    # --------------------------------------------------

    print("\n" + "=" * 80)
    print("VALIDATION BRIEF")
    print("=" * 80)

    if validation_brief:
        print(validation_brief)
    else:
        print(
            "validation_brief was not found "
            "in session state."
        )


    # --------------------------------------------------
    # Deck Content
    # --------------------------------------------------

    print("\n" + "=" * 80)
    print("DECK CONTENT")
    print("=" * 80)

    if deck_content:
        print(deck_content)
    else:
        print(
            "deck_content was not found "
            "in session state."
        )

    # ============================================================
# STEP 4: BUILD POWERPOINT
# ============================================================

if deck_content:
    deck_path = build_deck(deck_content)
    print("\n" + "=" * 80)
    print("POWERPOINT GENERATED")
    print("=" * 80)
    print(f"Deck saved to: {deck_path}")
else:
    print("Cannot build PowerPoint: deck_content was not found.")

    # --------------------------------------------------
    # Website HTML
    # --------------------------------------------------

    print("\n" + "=" * 80)
    print("WEBSITE HTML")
    print("=" * 80)

    if website_html:
        print(website_html)
    else:
        print(
            "website_html was not found "
            "in session state."
        )


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())