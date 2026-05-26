"""
Evacuation Routes
=================
POST /evacuation/assess  — Run EvacuNet on current sensor data
POST /evacuation/trigger — Force evacuation protocol
GET  /evacuation/status  — Current evacuation state
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import Field

from app.config import settings
from app.core.audit import log_audit_event
from app.core.evacuation_net import assess_stadium
from app.core.rate_limiter import limit_assessment_rate, limit_general_rate
from app.core.security import verify_admin_key
from app.models.evacuation import (
    EvacuationAssessment,
    EvacuationTrigger,
    SensorVector,
)
from app.services import firestore_service

router = APIRouter(prefix="/evacuation", tags=["evacuation"])


class AssessRequest(EvacuationTrigger):
    """Extended request with sensor vectors for assessment."""

    sensor_data: dict[str, SensorVector] = Field(default_factory=dict)


@router.post(
    "/assess",
    response_model=EvacuationAssessment,
    summary="Run EvacuNet hazard assessment",
    description="Evaluate all sensor data and return per-zone hazard probabilities.",
    dependencies=[Depends(limit_assessment_rate)],
)
async def assess_hazard(
    request: AssessRequest,
    _admin_key: str = Depends(verify_admin_key),
) -> EvacuationAssessment:
    """Run the EvacuNet neural network on provided sensor data."""
    stadium_id = request.stadium_id or settings.stadium_id

    if not request.sensor_data:
        # Return a default no-hazard assessment
        return EvacuationAssessment(
            stadium_id=stadium_id,
            should_evacuate=False,
            evacuation_message="No sensor data provided for assessment.",
        )

    zone_ids = list(request.sensor_data.keys())
    sensor_vectors = [request.sensor_data[z] for z in zone_ids]

    # Offload PyTorch inference and helper operations to thread pool
    assessment = await run_in_threadpool(assess_stadium, stadium_id, sensor_vectors, zone_ids)

    # If evacuation is recommended, push state to Firestore
    if assessment.should_evacuate:
        try:
            await run_in_threadpool(
                firestore_service.update_evacuation_state,
                stadium_id,
                {
                    "state": "ALERT",
                    "overall_probability": assessment.overall_probability,
                    "affected_zones": assessment.affected_zones,
                    "evacuation_message": assessment.evacuation_message,
                },
            )
            log_audit_event(
                action="auto_evacuation_alert",
                actor="system",
                status="SUCCESS",
                details={
                    "overall_probability": assessment.overall_probability,
                    "affected_zones": assessment.affected_zones,
                },
            )
        except Exception as exc:
            log_audit_event(
                action="auto_evacuation_alert",
                actor="system",
                status="FAILED",
                details={
                    "overall_probability": assessment.overall_probability,
                    "affected_zones": assessment.affected_zones,
                    "error": str(exc),
                },
            )

    return assessment


@router.post(
    "/trigger",
    summary="Force evacuation protocol",
    description="Manually trigger evacuation — requires authority override. Requires Admin API Key.",
    dependencies=[Depends(limit_general_rate)],
)
async def trigger_evacuation(
    trigger: EvacuationTrigger,
    _admin_key: str = Depends(verify_admin_key),
) -> dict:
    """Force the evacuation protocol regardless of sensor data."""
    stadium_id = trigger.stadium_id or settings.stadium_id

    state = {
        "state": "EVACUATING",
        "reason": trigger.reason,
        "affected_zones": trigger.affected_zones,
        "override_authority": trigger.override_authority,
        "evacuation_message": (
            f"EMERGENCY EVACUATION: {trigger.reason}. "
            "Proceed to the nearest emergency exit immediately."
        ),
    }

    try:
        await run_in_threadpool(firestore_service.update_evacuation_state, stadium_id, state)
        log_audit_event(
            action="manual_evacuation_trigger",
            actor=trigger.override_authority,
            status="SUCCESS",
            details={
                "reason": trigger.reason,
                "affected_zones": trigger.affected_zones,
            },
        )
    except Exception as exc:
        log_audit_event(
            action="manual_evacuation_trigger",
            actor=trigger.override_authority,
            status="FAILED",
            details={
                "reason": trigger.reason,
                "affected_zones": trigger.affected_zones,
                "error": str(exc),
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to update evacuation state in database",
        )

    return {
        "stadium_id": stadium_id,
        "evacuation": "TRIGGERED",
        **state,
    }


@router.get(
    "/status",
    summary="Current evacuation state",
    dependencies=[Depends(limit_general_rate)],
)
async def get_status(stadium_id: str | None = None) -> dict:
    sid = stadium_id or settings.stadium_id
    state = await run_in_threadpool(firestore_service.get_evacuation_state, sid)
    return state or {"state": "STANDBY", "stadium_id": sid}
