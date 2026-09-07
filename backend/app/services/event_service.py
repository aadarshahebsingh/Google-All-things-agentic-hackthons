"""Agent event log — every dashboard activity maps to a real backend event."""
from __future__ import annotations

import logging
import uuid

from ..models.opportunity import AgentEvent
from .firestore_service import get_firestore_service

log = logging.getLogger(__name__)
COLLECTION = "events"


def log_event(startup_id: str, agent: str, message: str, workflow_id: str = "", level: str = "INFO") -> AgentEvent:
    event = AgentEvent(
        event_id=uuid.uuid4().hex,
        startup_id=startup_id,
        workflow_id=workflow_id,
        agent=agent,
        message=message,
        level=level,
    )
    try:
        get_firestore_service().add(COLLECTION, event.model_dump(), doc_id=event.event_id)
    except Exception as exc:  # pragma: no cover
        log.error("Failed to persist event: %s", exc)
    log.info("[%s] %s: %s", startup_id, agent, message)
    return event


def get_events(startup_id: str) -> list[dict]:
    events = get_firestore_service().list(COLLECTION, "startup_id", startup_id)
    return sorted(events, key=lambda e: e.get("timestamp", ""))
