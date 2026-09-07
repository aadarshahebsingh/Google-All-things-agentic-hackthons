"""Google Calendar adapter with deduplication and a sandbox/demo fallback.

Real events are created via the Calendar API when OAuth credentials exist.
Demo mode uses a local mock calendar that is clearly labeled — never claiming
a real event was created when it was not.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timedelta

from ..config.settings import get_settings
from ..models.opportunity import Opportunity

log = logging.getLogger(__name__)


class CalendarResult(dict):
    pass


def _event_fingerprint(startup_id: str, title: str, date: str) -> str:
    raw = f"{startup_id}|{title}|{date}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class GoogleCalendarAdapter:
    """Real Google Calendar integration (OAuth refresh token)."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._service = None
        if self.settings.google_refresh_token and self.settings.google_client_id:
            try:
                from google.oauth2.credentials import Credentials
                from googleapiclient.discovery import build  # type: ignore

                creds = Credentials(
                    token=None,
                    refresh_token=self.settings.google_refresh_token,
                    client_id=self.settings.google_client_id,
                    client_secret=self.settings.google_client_secret,
                    token_uri="https://oauth2.googleapis.com/token",
                )
                self._service = build("calendar", "v3", credentials=creds)
                log.info("Google Calendar connected.")
            except Exception as exc:  # pragma: no cover
                log.warning("Calendar init failed (%s); using demo calendar.", exc)

    @property
    def backend(self) -> str:
        return "google_calendar" if self._service else "demo_calendar"

    def create_event(self, startup_id: str, title: str, due_date: str,
                     description: str = "") -> dict:
        fp = _event_fingerprint(startup_id, title, due_date)
        try:
            start = datetime.fromisoformat(due_date)
        except ValueError:
            start = datetime.now() + timedelta(days=7)
        end = start + timedelta(hours=1)

        if self._service:
            body = {
                "summary": title,
                "description": description,
                "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
                "id": fp,  # deterministic ID prevents duplicates on retry
            }
            try:
                created = self._service.events().insert(
                    calendarId=self.settings.google_calendar_id, body=body).execute()
                return {"status": "created", "backend": "google_calendar",
                        "event_id": created.get("id"), "html_link": created.get("htmlLink")}
            except Exception as exc:
                # 409 = already exists → treat as dedup success
                if "409" in str(exc):
                    return {"status": "already_exists", "backend": "google_calendar", "event_id": fp}
                log.warning("Calendar insert failed: %s", exc)
                return {"status": "error", "error_code": "CALENDAR_FAILURE", "retryable": True}
        # Demo fallback — clearly labeled
        return {"status": "created", "backend": "demo_calendar", "event_id": fp,
                "note": "DEMO: no real calendar event created (credentials not configured)."}


_adapter: GoogleCalendarAdapter | None = None


def get_calendar_adapter() -> GoogleCalendarAdapter:
    global _adapter
    if _adapter is None:
        _adapter = GoogleCalendarAdapter()
    return _adapter


def schedule_opportunity_prep(startup_id: str, opp: Opportunity) -> list[dict]:
    """Create the standard preparation timeline for an opportunity deadline."""
    if not opp.deadline:
        return []
    results = []
    try:
        deadline = datetime.fromisoformat(opp.deadline.replace("Z", ""))
    except ValueError:
        return [{"status": "error", "error_code": "INVALID_DATE", "message": opp.deadline}]

    plan = [
        (14, f"Research requirements: {opp.name}"),
        (10, f"Prepare pitch deck: {opp.name}"),
        (7, f"Test website/demo: {opp.name}"),
        (3, f"Final review: {opp.name}"),
        (1, f"Submission check: {opp.name}"),
        (0, f"DEADLINE: {opp.name}"),
    ]
    desc = (f"{opp.name}\nFit score: {opp.fit_score}/100\nApply: {opp.url}\n"
            f"Why fit: {opp.why_fit}")
    for days_before, title in plan:
        due = (deadline - timedelta(days=days_before)).date().isoformat()
        results.append(get_calendar_adapter().create_event(startup_id, title, due, desc))
    return results
