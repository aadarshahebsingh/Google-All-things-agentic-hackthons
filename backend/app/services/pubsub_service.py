"""Pub/Sub job publisher with an in-process background-runner fallback.

When Pub/Sub is configured, jobs are published to the topic and consumed by a
Cloud Run worker. When unavailable (local demo), jobs execute in-process via
FastAPI BackgroundTasks so the async architecture still demonstrates real
orchestration without faking Google infrastructure.
"""
from __future__ import annotations

import json
import logging

from ..config.settings import get_settings

log = logging.getLogger(__name__)

JOB_TYPES = [
    "research_job",
    "synthetic_market_job",
    "customer_discovery_job",
    "market_fit_job",
    "strategy_job",
    "collateral_job",
    "opportunity_job",
    "calendar_job",
]


class PubSubService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._publisher = None
        try:
            from google.cloud import pubsub_v1  # type: ignore

            project = self.settings.pubsub_project_id or self.settings.google_cloud_project
            self._publisher = pubsub_v1.PublisherClient()
            self._topic_path = self._publisher.topic_path(project, self.settings.pubsub_topic)
            log.info("Pub/Sub publisher ready (topic=%s)", self._topic_path)
        except Exception as exc:  # pragma: no cover - depends on env
            log.warning("Pub/Sub unavailable (%s); using in-process job runner.", exc)

    @property
    def backend(self) -> str:
        return "pubsub" if self._publisher else "in-process"

    def publish_job(self, job_type: str, payload: dict) -> bool:
        """Publish a job. Returns True if published to Pub/Sub, False if fallback."""
        message = json.dumps({"job_type": job_type, "payload": payload}).encode()
        if self._publisher:
            future = self._publisher.publish(self._topic_path, message)
            future.result(timeout=30)
            return True
        log.info("In-process job queued: %s", job_type)
        return False


_service: PubSubService | None = None


def get_pubsub_service() -> PubSubService:
    global _service
    if _service is None:
        _service = PubSubService()
    return _service
