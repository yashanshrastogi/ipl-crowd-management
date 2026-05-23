"""
Telemetry Routes
================
POST /pubsub  — Pub/Sub push subscription handler (returns empty 200)
POST /telemetry — Direct telemetry ingestion for testing
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status, Depends
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.core.rate_limiter import limit_general_rate

from app.models.telemetry import PubSubMessage, TelemetryPayload
from app.services.pubsub_service import process_direct_telemetry, process_pubsub_message

router = APIRouter(tags=["telemetry"])


@router.post(
    "/pubsub",
    status_code=status.HTTP_200_OK,
    summary="Pub/Sub push subscription handler",
    description=(
        "Receives push messages from Cloud Pub/Sub. Immediately returns "
        "HTTP 200 to acknowledge receipt and prevent duplicate retries."
    ),
    dependencies=[Depends(limit_general_rate)],
)
async def handle_pubsub_push(envelope: PubSubMessage) -> Response:
    """Decode and process a Pub/Sub push message.

    Per enterprise spec, this endpoint MUST return empty 200 immediately
    to eliminate duplicate streaming retries.
    """
    await run_in_threadpool(process_pubsub_message, envelope.message.data)
    return Response(status_code=status.HTTP_200_OK)


class DirectTelemetryResponse(BaseModel):
    status: str = "accepted"
    stadium_id: str = ""
    gate_id: str | None = None


@router.post(
    "/telemetry",
    response_model=DirectTelemetryResponse,
    summary="Direct telemetry ingestion",
    description="Accept telemetry payloads directly (bypassing Pub/Sub) for testing.",
    dependencies=[Depends(limit_general_rate)],
)
async def ingest_telemetry(payload: TelemetryPayload) -> DirectTelemetryResponse:
    """Process a telemetry payload submitted directly."""
    await run_in_threadpool(process_direct_telemetry, payload)
    return DirectTelemetryResponse(
        status="accepted",
        stadium_id=payload.stadium_id,
        gate_id=payload.gate_id,
    )

