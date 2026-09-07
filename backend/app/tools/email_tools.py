"""Email/outreach adapter with rate limiting, opt-out and audit logging.

Never impersonates a human: messages clearly identify the sender as an AI
research assistant. Rate limited to prevent spam. Demo mode logs instead of
sending.
"""
from __future__ import annotations

import logging
import time

log = logging.getLogger(__name__)

RATE_LIMIT_PER_MINUTE = 5
_send_timestamps: list[float] = []


def check_rate_limit() -> bool:
    # Reserve a send slot when returning True (prevents burst sends).
    now = time.time()
    global _send_timestamps
    _send_timestamps = [t for t in _send_timestamps if now - t < 60]
    if len(_send_timestamps) < RATE_LIMIT_PER_MINUTE:
        _send_timestamps.append(now)
        return True
    return False


def build_outreach_message(candidate_name: str, topic: str) -> str:
    """Transparent outreach â€” identifies as AI research, offers opt-out."""
    return (
        f"Hi {candidate_name},\n\n"
        f"I'm an AI research assistant helping validate a startup idea about {topic}. "
        f"We noticed public discussion of challenges you've shared around this area. "
        f"Would you be open to a short research conversation? "
        f"Reply OPT-OUT at any time and we will not contact you again.\n\n"
        f"â€” FounderShortcut research agent (automated message)"
    )


def send_email(to_channel: str, body: str) -> dict:
    """Send via configured provider. Demo mode records without sending."""
    if not check_rate_limit():
        return {"status": "SKIPPED_RATE_LIMITED", "sent": False}
    settings = get_settings()
    if settings.email_provider_api_key:
        try:
            import requests

            resp = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {settings.email_provider_api_key}"},
                json={
                    "personalizations": [{"to": [{"email": to_channel.replace("email:", "")}]}],
                    "from": {"email": "research@foundershortcut.example"},
                    "subject": "Startup research interview request",
                    "content": [{"type": "text/plain", "value": body}],
                },
                timeout=10,
            )
            resp.raise_for_status()
            _send_timestamps.append(time.time())
            return {"status": "SENT", "sent": True}
        except Exception as exc:
            log.warning("Email send failed: %s", exc)
            return {"status": "FAILED", "sent": False, "error": str(exc)}
    log.info("DEMO email (not sent): to=%s body=%s...", to_channel, body[:60])
    return {"status": "DEMO_LOGGED", "sent": False,
            "note": "DEMO: message recorded but not sent (no email provider configured)."}


def get_settings():
    from ..config.settings import get_settings as _gs

    return _gs()
