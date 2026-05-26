"""
Crowdsource Routes
==================
POST /reports — Submit spectator field reports
GET  /reports — Retrieve recent reports (paginated)
"""

from __future__ import annotations

import html

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.core.rate_limiter import limit_general_rate
from app.models.crowd import CrowdsourcedReport
from app.services import firestore_service
from fastapi import Depends

router = APIRouter(prefix="/reports", tags=["crowdsource"])

# V-10: Valid enum values for server-side validation
VALID_SEVERITIES = {"info", "warning", "critical"}
VALID_REPORTER_TYPES = {"spectator", "security", "system"}


@router.post(
    "",
    summary="Submit a field report",
    description="Spectators and security staff can submit real-time field reports.",
    dependencies=[Depends(limit_general_rate)],
)
async def create_report(
    report: CrowdsourcedReport,
    stadium_id: str | None = None,
) -> dict:
    sid = stadium_id or settings.stadium_id

    # V-10: Validate enum fields server-side
    if report.severity not in VALID_SEVERITIES:
        raise HTTPException(400, f"Invalid severity. Must be one of: {', '.join(VALID_SEVERITIES)}")
    if report.reporter_type not in VALID_REPORTER_TYPES:
        raise HTTPException(400, f"Invalid reporter_type. Must be one of: {', '.join(VALID_REPORTER_TYPES)}")

    # V-10: Sanitize ALL user-controlled string fields to prevent stored XSS
    for field in ("message", "zone_id", "gate_id", "severity", "reporter_type"):
        value = getattr(report, field, "")
        if isinstance(value, str):
            setattr(report, field, html.escape(value.strip()))

    report_id = await run_in_threadpool(
        firestore_service.add_report, sid, report.model_dump()
    )
    return {
        "status": "submitted",
        "report_id": report_id,
        "stadium_id": sid,
    }



@router.get(
    "",
    summary="Get recent reports",
    description="Retrieve the most recent crowdsourced field reports.",
    dependencies=[Depends(limit_general_rate)],
)
async def list_reports(
    stadium_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200, description="Max reports to return (1-200)"),
) -> dict:
    sid = stadium_id or settings.stadium_id
    reports = await run_in_threadpool(
        firestore_service.get_recent_reports, sid, limit=limit
    )
    return {
        "stadium_id": sid,
        "count": len(reports),
        "reports": reports,
    }
