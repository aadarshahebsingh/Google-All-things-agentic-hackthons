"""Firestore service with a thread-safe in-memory fallback.

Firestore is the source of truth when credentials are available; otherwise the
fallback keeps local/demo runs working without pretending to be Firestore.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from ..config.settings import get_settings

log = logging.getLogger(__name__)


class MemoryStore:
    """Fallback store. Not durable — used only when Firestore is unavailable."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, dict[str, dict[str, Any]]] = {}

    def _col(self, collection: str) -> dict[str, dict[str, Any]]:
        with self._lock:
            return self._data.setdefault(collection, {})

    def set(self, collection: str, doc_id: str, data: dict[str, Any]) -> None:
        self._col(collection)[doc_id] = dict(data)

    def get(self, collection: str, doc_id: str) -> dict[str, Any] | None:
        doc = self._col(collection).get(doc_id)
        return dict(doc) if doc else None

    def update(self, collection: str, doc_id: str, patch: dict[str, Any]) -> None:
        col = self._col(collection)
        if doc_id in col:
            col[doc_id].update(patch)

    def list(self, collection: str, field: str | None = None, value: Any = None) -> list[dict[str, Any]]:
        docs = list(self._col(collection).values())
        if field is not None:
            docs = [d for d in docs if d.get(field) == value]
        return [dict(d) for d in docs]


class FirestoreService:
    """Thin wrapper over google-cloud-firestore with graceful degradation."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._fs = None
        self._memory = MemoryStore()
        try:
            from google.cloud import firestore  # type: ignore

            self._fs = firestore.Client(
                project=self.settings.google_cloud_project,
                database=self.settings.firestore_database,
            )
            log.info("Firestore connected (project=%s)", self.settings.google_cloud_project)
        except Exception as exc:  # pragma: no cover - depends on env
            log.warning("Firestore unavailable (%s); using in-memory fallback.", exc)

    @property
    def backend(self) -> str:
        return "firestore" if self._fs else "memory"

    def set(self, collection: str, doc_id: str, data: dict[str, Any]) -> None:
        if self._fs:
            self._fs.collection(collection).document(doc_id).set(data)
        else:
            self._memory.set(collection, doc_id, data)

    def get(self, collection: str, doc_id: str) -> dict[str, Any] | None:
        if self._fs:
            snap = self._fs.collection(collection).document(doc_id).get()
            return snap.to_dict() if snap.exists else None
        return self._memory.get(collection, doc_id)

    def update(self, collection: str, doc_id: str, patch: dict[str, Any]) -> None:
        if self._fs:
            self._fs.collection(collection).document(doc_id).set(patch, merge=True)
        else:
            self._memory.update(collection, doc_id, patch)

    def add(self, collection: str, data: dict[str, Any], doc_id: str | None = None) -> str:
        if doc_id is None:
            import uuid

            doc_id = uuid.uuid4().hex
        self.set(collection, doc_id, data)
        return doc_id

    def list(self, collection: str, field: str | None = None, value: Any = None) -> list[dict[str, Any]]:
        if self._fs:
            query = self._fs.collection(collection)
            if field is not None:
                query = query.where(field, "==", value)
            return [doc.to_dict() for doc in query.stream()]
        return self._memory.list(collection, field, value)


_service: FirestoreService | None = None


def get_firestore_service() -> FirestoreService:
    global _service
    if _service is None:
        _service = FirestoreService()
    return _service
