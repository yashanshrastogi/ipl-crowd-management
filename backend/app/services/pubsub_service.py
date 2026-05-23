"""
Pub/Sub Service
===============
Handles Cloud Pub/Sub push subscription messages.  The push endpoint
MUST return HTTP 200 immediately to acknowledge receipt and prevent
duplicate streaming retries (per enterprise spec).

Flow:  Pub/Sub push → decode base64 → parse telemetry → process → ack
"""

from __future__ import annotations

import base64
import json
import logging

from app.core.crowd_physics import compute_gate_metrics
from app.models.telemetry import TelemetryPayload
from app.services import bigquery_service, firestore_service
from app.config import settings

logger = logging.getLogger(__name__)


def process_pubsub_message(raw_data: str) -> TelemetryPayload | None:
    """Decode a base64 Pub/Sub message and run the processing pipeline.

    Parameters
    ----------
    raw_data : str
        Base64-encoded JSON string from the Pub/Sub push envelope.

    Returns
    -------
    TelemetryPayload | None
        Parsed payload, or None if decoding / validation fails.
    """
    try:
        decoded = base64.b64decode(raw_data).decode("utf-8")
        payload_dict = json.loads(decoded)
        payload = TelemetryPayload(**payload_dict)
    except Exception:
        logger.exception("Failed to decode Pub/Sub message")
        return None

    _process_telemetry(payload)
    return payload


def process_direct_telemetry(payload: TelemetryPayload) -> None:
    """Process a telemetry payload submitted directly (non-Pub/Sub path)."""
    _process_telemetry(payload)


def _process_telemetry(payload: TelemetryPayload) -> None:
    """Internal: run crowd physics, update Firestore, append to BigQuery."""
    stadium_id = payload.stadium_id or settings.stadium_id

    if payload.gate_id and payload.crowd_density is not None:
        # Compute derived crowd physics
        gate_physics = compute_gate_metrics(
            density=payload.crowd_density,
            effective_width=3.0,  # Default; can be per-gate in production
            wait_time_minutes=0.0,  # Estimated from queue model
        )

        gate_doc = {
            "density": payload.crowd_density,
            "estimated_count": payload.estimated_count,
            "mean_velocity": payload.mean_velocity,
            **gate_physics,
            "zone_id": payload.zone_id,
        }

        # Update Firestore (real-time state)
        try:
            firestore_service.update_gate_status(stadium_id, payload.gate_id, gate_doc)
        except Exception:
            logger.exception("Firestore update failed for gate %s", payload.gate_id)

    # Append raw telemetry to BigQuery (analytical warehouse)
    try:
        bq_row = {
            "stadium_id": stadium_id,
            "gate_id": payload.gate_id or "",
            "zone_id": payload.zone_id,
            "timestamp": payload.timestamp.isoformat(),
            "density": payload.crowd_density,
            "velocity": payload.mean_velocity,
            "estimated_count": payload.estimated_count,
            "sensor_readings": [
                {
                    "sensor_type": r.sensor_type.value,
                    "value": r.value,
                    "unit": r.unit,
                }
                for r in payload.readings
            ],
        }
        bigquery_service.insert_telemetry_row(bq_row)
    except Exception:
        logger.exception("BigQuery insert failed")
