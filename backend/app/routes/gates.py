"""
Gate Routes
===========
GET  /gates            — All gate statuses with computed physics
GET  /gates/{gate_id}  — Single gate detail
POST /gates/{gate_id}/signage — Update dynamic signage
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.core.audit import log_audit_event
from app.core.crowd_physics import compute_gate_metrics
from app.core.rate_limiter import limit_general_rate
from app.core.security import verify_admin_key
from app.models.crowd import SignageUpdate
from app.services import firestore_service

router = APIRouter(prefix="/gates", tags=["gates"])


@router.get(
    "",
    summary="Get all gate statuses",
    description="Retrieve live metrics and computed crowd physics for every gate.",
    dependencies=[Depends(limit_general_rate)],
)
async def get_all_gates(stadium_id: str | None = None) -> dict:
    sid = stadium_id or settings.stadium_id
    gates = await run_in_threadpool(firestore_service.get_all_gates, sid)

    # Enrich each gate with computed physics
    for gate in gates:
        density = gate.get("density", 0)
        width = gate.get("effective_width", 3.0)
        wait = gate.get("wait_time_minutes", 0)
        physics = compute_gate_metrics(density, width, wait)
        gate.update(physics)

    return {
        "stadium_id": sid,
        "gate_count": len(gates),
        "gates": gates,
    }


@router.get(
    "/{gate_id}",
    summary="Get single gate status",
    description="Retrieve detailed metrics for a specific gate.",
    dependencies=[Depends(limit_general_rate)],
)
async def get_gate(gate_id: str, stadium_id: str | None = None) -> dict:
    sid = stadium_id or settings.stadium_id
    gate = await run_in_threadpool(firestore_service.get_gate, sid, gate_id)
    if gate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gate '{gate_id}' not found in stadium '{sid}'",
        )
    density = gate.get("density", 0)
    width = gate.get("effective_width", 3.0)
    wait = gate.get("wait_time_minutes", 0)
    physics = compute_gate_metrics(density, width, wait)
    gate.update(physics)
    return gate


@router.post(
    "/{gate_id}/signage",
    summary="Update dynamic signage",
    description="Send a message to the physical LED signage at a gate. Requires Admin API Key.",
    dependencies=[Depends(limit_general_rate)],
)
async def update_signage(
    gate_id: str,
    update: SignageUpdate,
    _admin_key: str = Depends(verify_admin_key),
) -> dict:
    sid = settings.stadium_id
    try:
        await run_in_threadpool(
            firestore_service.update_gate_status,
            sid,
            gate_id,
            {
                "signage_message": update.message,
                "signage_active": True,
                "signage_priority": update.priority,
            },
        )
        log_audit_event(
            action="update_signage",
            actor="admin",
            status="SUCCESS",
            details={"gate_id": gate_id, "message": update.message, "priority": update.priority},
        )
    except Exception as exc:
        log_audit_event(
            action="update_signage",
            actor="admin",
            status="FAILED",
            details={"gate_id": gate_id, "message": update.message, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update dynamic signage",
        )
    return {
        "gate_id": gate_id,
        "signage_status": "UPDATED",
        "displayed_text": update.message,
    }
