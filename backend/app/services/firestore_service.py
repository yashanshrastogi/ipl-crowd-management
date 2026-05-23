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

from google.cloud import firestore  # type: ignore[import-untyped]

from app.config import settings

logger = logging.getLogger(__name__)

_client: firestore.Client | None = None


def _get_client() -> firestore.Client:
    """Lazy-initialise a Firestore client singleton."""
    global _client  # noqa: PLW0603
    if _client is None:
        _client = firestore.Client(
            project=settings.google_cloud_project,
            database=settings.firestore_database,
        )
        logger.info("Firestore client initialised (project=%s)", settings.google_cloud_project)
    return _client


# ── Gate Operations ───────────────────────────────────────────────────────────


def update_gate_status(stadium_id: str, gate_id: str, metrics: dict[str, Any]) -> None:
    """Write or merge gate metrics into Firestore.

    Path: stadiums/{stadium_id}/gates/{gate_id}
    """
    db = _get_client()
    ref = db.collection("stadiums").document(stadium_id).collection("gates").document(gate_id)
    metrics["updated_at"] = datetime.now(timezone.utc).isoformat()
    ref.set(metrics, merge=True)
    logger.debug("Gate %s/%s updated", stadium_id, gate_id)


def get_gate(stadium_id: str, gate_id: str) -> dict[str, Any] | None:
    """Read a single gate document."""
    db = _get_client()
    doc = (
        db.collection("stadiums")
        .document(stadium_id)
        .collection("gates")
        .document(gate_id)
        .get()
    )
    return doc.to_dict() if doc.exists else None


def get_all_gates(stadium_id: str) -> list[dict[str, Any]]:
    """Return all gate documents for a stadium."""
    db = _get_client()
    docs = (
        db.collection("stadiums")
        .document(stadium_id)
        .collection("gates")
        .stream()
    )
    return [{"gate_id": d.id, **d.to_dict()} for d in docs]


def update_strict_protocol(
    stadium_id: str,
    gate_id: str,
    active: bool,
    message: str = "",
    banned_items: list[str] | None = None,
) -> None:
    """Toggle the Strict Protocol flag on a gate."""
    db = _get_client()
    ref = db.collection("stadiums").document(stadium_id).collection("gates").document(gate_id)
    payload: dict[str, Any] = {
        "strict_protocol": {
            "active": active,
            "message": message or "Prepare credentials. Remove banned items before queuing.",
            "banned_items": banned_items or ["bags", "coins", "bottles", "umbrellas"],
            "activated_at": datetime.now(timezone.utc).isoformat() if active else None,
        }
    }
    ref.set(payload, merge=True)
    logger.info("Strict Protocol %s for gate %s/%s", "ACTIVATED" if active else "DEACTIVATED", stadium_id, gate_id)


# ── Crowdsourced Reports ─────────────────────────────────────────────────────


def add_report(stadium_id: str, report: dict[str, Any]) -> str:
    """Insert a spectator field report.  Returns the generated report_id."""
    db = _get_client()
    report_id = report.get("report_id") or str(uuid4())
    report["report_id"] = report_id
    report["timestamp"] = report.get("timestamp", datetime.now(timezone.utc).isoformat())
    ref = (
        db.collection("stadiums")
        .document(stadium_id)
        .collection("reports")
        .document(report_id)
    )
    ref.set(report)
    return report_id


def get_recent_reports(stadium_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Fetch most recent reports, newest first."""
    db = _get_client()
    docs = (
        db.collection("stadiums")
        .document(stadium_id)
        .collection("reports")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [{"report_id": d.id, **d.to_dict()} for d in docs]


# ── Evacuation State ─────────────────────────────────────────────────────────


def update_evacuation_state(stadium_id: str, state: dict[str, Any]) -> None:
    """Write the current evacuation state document."""
    db = _get_client()
    ref = db.collection("stadiums").document(stadium_id).collection("evacuation").document("current")
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    ref.set(state, merge=True)


def get_evacuation_state(stadium_id: str) -> dict[str, Any] | None:
    """Read the current evacuation state."""
    db = _get_client()
    doc = (
        db.collection("stadiums")
        .document(stadium_id)
        .collection("evacuation")
        .document("current")
        .get()
    )
    return doc.to_dict() if doc.exists else None
