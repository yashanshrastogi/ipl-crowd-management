"""
Agent Routes
============
POST /agents/dispatch — Send a natural-language directive to the orchestrator
GET  /agents/status   — Current agent state and recent actions
POST /agents/security-scan — Run gate security analysis
POST /agents/reroute  — Find alternative route from congested gate
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.agents import gate_security, orchestrator, routing
from app.config import settings
from app.core.audit import log_audit_event
from app.core.rate_limiter import limit_dispatch_rate, limit_general_rate
from app.core.security import verify_admin_key

router = APIRouter(prefix="/agents", tags=["agents"])


class DispatchRequest(BaseModel):
    prompt: str
    stadium_id: str = ""


class RerouteRequest(BaseModel):
    congested_gate_id: str
    stadium_id: str = ""


@router.post(
    "/dispatch",
    summary="Dispatch orchestrator agent",
    description=(
        "Send a natural-language directive to the master orchestrator. "
        "The agent will inspect gate statuses, make routing decisions, "
        "and execute tools autonomously. Requires Admin API Key."
    ),
    dependencies=[Depends(limit_dispatch_rate)],
)
async def dispatch_agent(
    request: DispatchRequest,
    _admin_key: str = Depends(verify_admin_key),
) -> dict:
    """Forward prompt to orchestrator for autonomous tool execution."""
    try:
        result = await orchestrator.dispatch(request.prompt)
        log_audit_event(
            action="dispatch_agent",
            actor="admin",
            status="SUCCESS",
            details={"prompt": request.prompt, "status": result.get("status")},
        )
        return result
    except Exception as exc:
        log_audit_event(
            action="dispatch_agent",
            actor="admin",
            status="FAILED",
            details={"prompt": request.prompt, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent dispatch failed",
        )


@router.get(
    "/status",
    summary="Agent system status",
)
async def get_status() -> dict:
    return {
        "orchestrator": "active",
        "gate_security_agent": "active",
        "routing_agent": "active",
        "stadium_id": settings.stadium_id,
    }


@router.post(
    "/security-scan",
    summary="Run gate security analysis",
    description="Analyse gate loading for asymmetry and activate Strict Protocol. Requires Admin API Key.",
    dependencies=[Depends(limit_general_rate)],
)
async def security_scan(
    stadium_id: str | None = None,
    _admin_key: str = Depends(verify_admin_key),
) -> dict:
    try:
        result = await run_in_threadpool(gate_security.run_security_scan, stadium_id)
        log_audit_event(
            action="security_scan",
            actor="admin",
            status="SUCCESS",
            details={"stadium_id": stadium_id, "actions_taken": len(result.get("actions", []))},
        )
        return result
    except Exception as exc:
        log_audit_event(
            action="security_scan",
            actor="admin",
            status="FAILED",
            details={"stadium_id": stadium_id, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Security scan failed",
        )


@router.post(
    "/reroute",
    summary="Find alternative route",
    description="Compute the best alternative gate and walking route. Requires Admin API Key.",
    dependencies=[Depends(limit_general_rate)],
)
async def reroute(
    request: RerouteRequest,
    _admin_key: str = Depends(verify_admin_key),
) -> dict:
    try:
        result = await run_in_threadpool(
            routing.reroute_crowd,
            request.congested_gate_id,
            request.stadium_id or None,
        )
        log_audit_event(
            action="reroute",
            actor="admin",
            status="SUCCESS",
            details={
                "congested_gate_id": request.congested_gate_id,
                "recommended_gate": result.get("recommended_gate"),
            },
        )
        return result
    except Exception as exc:
        log_audit_event(
            action="reroute",
            actor="admin",
            status="FAILED",
            details={"congested_gate_id": request.congested_gate_id, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Rerouting calculation failed",
        )
