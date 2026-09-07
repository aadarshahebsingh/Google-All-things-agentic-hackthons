"""Voice provider adapter architecture.

VoiceProvider is the interface; TwilioAdapter uses the real Twilio API when
credentials exist; DemoAdapter simulates a consenting test participant for
hackathon demos (clearly labeled — never presented as a real call).
"""
from __future__ import annotations

import logging
from typing import Protocol

log = logging.getLogger(__name__)


class VoiceProvider(Protocol):
    def place_call(self, to_channel: str, script: list[dict]) -> dict: ...
    @property
    def name(self) -> str: ...


class TwilioAdapter:
    """Real Twilio voice calls. Requires credentials + consented recipient."""

    def __init__(self) -> None:
        from ..config.settings import get_settings

        s = get_settings()
        self._client = None
        if s.twilio_account_sid and s.twilio_auth_token and s.twilio_phone_number:
            try:
                from twilio.rest import Client  # type: ignore

                self._client = Client(s.twilio_account_sid, s.twilio_auth_token)
            except Exception as exc:  # pragma: no cover
                log.warning("Twilio init failed: %s", exc)

    @property
    def name(self) -> str:
        return "twilio"

    def place_call(self, to_channel: str, script: list[dict]) -> dict:
        if not self._client:
            return {"status": "error", "error_code": "NO_CREDENTIALS",
                    "message": "Twilio not configured", "retryable": False}
        try:
            from ..config.settings import get_settings

            s = get_settings()
            call = self._client.calls.create(
                to=to_channel.replace("phone:", ""),
                from_=s.twilio_phone_number,
                twiml=_build_twiml(script),
            )
            return {"status": "initiated", "call_sid": call.sid, "provider": "twilio"}
        except Exception as exc:
            return {"status": "error", "error_code": "CALL_FAILED", "message": str(exc), "retryable": True}


class DemoAdapter:
    """Simulated voice interview with a scripted consenting test participant."""

    @property
    def name(self) -> str:
        return "demo"

    def place_call(self, to_channel: str, script: list[dict]) -> dict:
        # Simulated responses from a controlled test participant.
        responses = [
            {"question": q["text"],
             "answer": _DEMO_ANSWERS.get(q.get("intent", "general"),
                                         "I currently handle this manually; it takes a lot of time."),
             "simulated": True}
            for q in script
        ]
        return {"status": "completed", "provider": "demo", "responses": responses,
                "note": "SIMULATED interview with a controlled test participant."}


_DEMO_ANSWERS = {
    "current_process": "I mostly find options through job portals and LinkedIn; it's slow and repetitive.",
    "frustration": "Filtering irrelevant listings wastes hours every week.",
    "personalization": "Personalized recommendations would be very useful — that's the main gap.",
    "trust_automation": "I'd want review before anything automatic is submitted on my behalf.",
    "pricing": "Maybe around a hundred rupees a month if it really saves time.",
    "objection": "I'd worry about accuracy of matches.",
}


def _build_twiml(script: list[dict]) -> str:
    lines = ["<?xml version='1.0' encoding='UTF-8'?><Response>"]
    for q in script:
        lines.append(f"<Say>{q['text']}</Say><Pause length='4'/>")
    lines.append("<Say>Thank you for your time.</Say></Response>")
    return "".join(lines)


def get_voice_provider() -> VoiceProvider:
    """Prefer real Twilio when configured; fall back to demo adapter."""
    twilio = TwilioAdapter()
    if twilio._client is not None:
        return twilio
    return DemoAdapter()
