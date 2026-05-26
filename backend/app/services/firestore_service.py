"""
Firestore Service
=================
Async wrapper around Google Cloud Firestore for real-time gate state
management.  Uses the Native-mode Firestore client with snapshot
listeners for sub-second push to connected web clients.

Collection hierarchy
--------------------
stadiums/{stadium_id}/gates/{gate_id}
stadiums/{stadium_id}/reports/{report_id}
stadiums/{stadium_id}/evacuation/current
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from google.api_core import exceptions as google_exceptions  # type: ignore[import-untyped]
from google.auth import exceptions as auth_exceptions  # type: ignore[import-untyped]
from google.cloud import firestore  # type: ignore[import-untyped]

from app.config import settings

logger = logging.getLogger(__name__)

_client: firestore.Client | None = None
_client_unavailable = False
_local_store: dict[str, dict[str, Any]] = {}


def _is_local_fallback_allowed() -> bool:
    return settings.app_env != "production"


def _stadium_store(stadium_id: str) -> dict[str, Any]:
    stadium = _local_store.setdefault(stadium_id, {})
    stadium.setdefault("gates", {})
    stadium.setdefault("reports", {})
    stadium.setdefault("evacuation", {})
    return stadium


def _get_client() -> firestore.Client | None:
    """Lazy-initialise a Firestore client singleton."""
    global _client, _client_unavailable  # noqa: PLW0603
    if _client_unavailable:
        return None
    if _client is None:
        try:
            _client = firestore.Client(
                project=settings.google_cloud_project,
                database=settings.firestore_database,
            )
            logger.info("Firestore client initialised (project=%s)", settings.google_cloud_project)
        except auth_exceptions.GoogleAuthError:
            if not _is_local_fallback_allowed():
                raise
            _client_unavailable = True
            logger.warning("Firestore credentials unavailable; using in-memory local store")
            return None
    return _client


def _is_recoverable_service_error(exc: Exception) -> bool:
    return isinstance(
        exc,
        (
            auth_exceptions.GoogleAuthError,
            google_exceptions.GoogleAPICallError,
            google_exceptions.RetryError,
        ),
    )


def _fallback_after_error(exc: Exception) -> bool:
    global _client_unavailable  # noqa: PLW0603
    if not _is_local_fallback_allowed() or not _is_recoverable_service_error(exc):
        return False
    _client_unavailable = True
    logger.warning("Firestore unavailable; falling back to in-memory local store: %s", exc)
    return True


# ── Gate Operations ───────────────────────────────────────────────────────────


def update_gate_status(stadium_id: str, gate_id: str, metrics: dict[str, Any]) -> None:
    """Write or merge gate metrics into Firestore.

    Path: stadiums/{stadium_id}/gates/{gate_id}
    """
    metrics = {**metrics, "updated_at": datetime.now(timezone.utc).isoformat()}
    db = _get_client()
    if db is None:
        _stadium_store(stadium_id)["gates"].setdefault(gate_id, {}).update(metrics)
        return
    try:
        ref = db.collection("stadiums").document(stadium_id).collection("gates").document(gate_id)
        ref.set(metrics, merge=True)
    except Exception as exc:
        if not _fallback_after_error(exc):
            raise
        _stadium_store(stadium_id)["gates"].setdefault(gate_id, {}).update(metrics)
    logger.debug("Gate %s/%s updated", stadium_id, gate_id)


def get_gate(stadium_id: str, gate_id: str) -> dict[str, Any] | None:
    """Read a single gate document."""
    db = _get_client()
    if db is None:
        gate = _stadium_store(stadium_id)["gates"].get(gate_id)
        return {"gate_id": gate_id, **gate} if gate else None
    try:
        doc = (
            db.collection("stadiums")
            .document(stadium_id)
            .collection("gates")
            .document(gate_id)
            .get()
        )
        return doc.to_dict() if doc.exists else None
    except Exception as exc:
        if not _fallback_after_error(exc):
            raise
        gate = _stadium_store(stadium_id)["gates"].get(gate_id)
        return {"gate_id": gate_id, **gate} if gate else None


def get_all_gates(stadium_id: str) -> list[dict[str, Any]]:
    """Return all gate documents for a stadium."""
    db = _get_client()
    if db is None:
        return [
            {"gate_id": gate_id, **gate}
            for gate_id, gate in _stadium_store(stadium_id)["gates"].items()
        ]
    try:
        docs = (
            db.collection("stadiums")
            .document(stadium_id)
            .collection("gates")
            .stream()
        )
        return [{"gate_id": d.id, **d.to_dict()} for d in docs]
    except Exception as exc:
        if not _fallback_after_error(exc):
            raise
        return [
            {"gate_id": gate_id, **gate}
            for gate_id, gate in _stadium_store(stadium_id)["gates"].items()
        ]


def update_strict_protocol(
    stadium_id: str,
    gate_id: str,
    active: bool,
    message: str = "",
    banned_items: list[str] | None = None,
) -> None:
    """Toggle the Strict Protocol flag on a gate."""
    payload: dict[str, Any] = {
        "strict_protocol": {
            "active": active,
            "message": message or "Prepare credentials. Remove banned items before queuing.",
            "banned_items": banned_items or ["bags", "coins", "bottles", "umbrellas"],
            "activated_at": datetime.now(timezone.utc).isoformat() if active else None,
        }
    }
    db = _get_client()
    if db is None:
        _stadium_store(stadium_id)["gates"].setdefault(gate_id, {}).update(payload)
        return
    try:
        ref = db.collection("stadiums").document(stadium_id).collection("gates").document(gate_id)
        ref.set(payload, merge=True)
    except Exception as exc:
        if not _fallback_after_error(exc):
            raise
        _stadium_store(stadium_id)["gates"].setdefault(gate_id, {}).update(payload)
    logger.info("Strict Protocol %s for gate %s/%s", "ACTIVATED" if active else "DEACTIVATED", stadium_id, gate_id)


# ── Crowdsourced Reports ─────────────────────────────────────────────────────


def add_report(stadium_id: str, report: dict[str, Any]) -> str:
    """Insert a spectator field report.  Returns the generated report_id."""
    report_id = report.get("report_id") or str(uuid4())
    report["report_id"] = report_id
    report["timestamp"] = report.get("timestamp", datetime.now(timezone.utc).isoformat())
    db = _get_client()
    if db is None:
        _stadium_store(stadium_id)["reports"][report_id] = dict(report)
        return report_id
    try:
        ref = (
            db.collection("stadiums")
            .document(stadium_id)
            .collection("reports")
            .document(report_id)
        )
        ref.set(report)
    except Exception as exc:
        if not _fallback_after_error(exc):
            raise
        _stadium_store(stadium_id)["reports"][report_id] = dict(report)
    return report_id


def get_recent_reports(stadium_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Fetch most recent reports, newest first."""
    db = _get_client()
    if db is None:
        reports = list(_stadium_store(stadium_id)["reports"].items())
        reports.sort(key=lambda item: item[1].get("timestamp", ""), reverse=True)
        return [{"report_id": report_id, **report} for report_id, report in reports[:limit]]
    try:
        docs = (
            db.collection("stadiums")
            .document(stadium_id)
            .collection("reports")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [{"report_id": d.id, **d.to_dict()} for d in docs]
    except Exception as exc:
        if not _fallback_after_error(exc):
            raise
        reports = list(_stadium_store(stadium_id)["reports"].items())
        reports.sort(key=lambda item: item[1].get("timestamp", ""), reverse=True)
        return [{"report_id": report_id, **report} for report_id, report in reports[:limit]]


# ── Evacuation State ─────────────────────────────────────────────────────────


def update_evacuation_state(stadium_id: str, state: dict[str, Any]) -> None:
    """Write the current evacuation state document."""
    state = {**state, "updated_at": datetime.now(timezone.utc).isoformat()}
    db = _get_client()
    if db is None:
        _stadium_store(stadium_id)["evacuation"].update(state)
        return
    try:
        ref = db.collection("stadiums").document(stadium_id).collection("evacuation").document("current")
        ref.set(state, merge=True)
    except Exception as exc:
        if not _fallback_after_error(exc):
            raise
        _stadium_store(stadium_id)["evacuation"].update(state)


def get_evacuation_state(stadium_id: str) -> dict[str, Any] | None:
    """Read the current evacuation state."""
    db = _get_client()
    if db is None:
        state = _stadium_store(stadium_id)["evacuation"]
        return dict(state) if state else None
    try:
        doc = (
            db.collection("stadiums")
            .document(stadium_id)
            .collection("evacuation")
            .document("current")
            .get()
        )
        return doc.to_dict() if doc.exists else None
    except Exception as exc:
        if not _fallback_after_error(exc):
            raise
        state = _stadium_store(stadium_id)["evacuation"]
        return dict(state) if state else None
