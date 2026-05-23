"""
Crowdsource Routes
==================
POST /reports — Submit spectator field reports
GET  /reports — Retrieve recent reports (paginated)
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.models.crowd import CrowdsourcedReport
from app.services import firestore_service

router = APIRouter(prefix="/reports", tags=["crowdsource"])


import html

@router.post(
    "",
    summary="Submit a field report",
    description="Spectators and security staff can submit real-time field reports.",
)
async def create_report(
    report: CrowdsourcedReport,
    stadium_id: str | None = None,
) -> dict:
    sid = stadium_id or settings.stadium_id
    # Escape message to prevent stored XSS attacks
    report.message = html.escape(report.message.strip())
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
)
async def list_reports(
    stadium_id: str | None = None,
    limit: int = 50,
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

