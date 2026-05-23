"""
IPL Crowd Management — FastAPI Application
===========================================
Enterprise-grade microservice for real-time crowd dynamics monitoring,
multi-agent orchestration, and emergency evacuation management.

Endpoints are organised into routers:
  /pubsub, /telemetry  — Telemetry ingestion
  /gates               — Gate status & signage
  /evacuation          — EvacuNet hazard assessment
  /agents              — Gemini-powered agent orchestration
  /reports             — Crowdsourced field reports
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import agents, crowdsource, evacuation, gates, telemetry

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup / shutdown lifecycle hooks."""
    logger.info("═" * 60)
    logger.info("  IPL Crowd Management System — Starting Up")
    logger.info("  Project : %s", settings.google_cloud_project)
    logger.info("  Stadium : %s", settings.stadium_id)
    logger.info("  Env     : %s", settings.app_env)
    logger.info("═" * 60)

    # Optionally bootstrap BigQuery schema on startup
    if settings.app_env != "test":
        try:
            from app.services.bigquery_service import ensure_dataset_and_table
            ensure_dataset_and_table()
            logger.info("BigQuery schema bootstrap complete")
        except Exception:
            logger.warning("BigQuery bootstrap skipped (service may not be available)")

    yield

    logger.info("IPL Crowd Management System — Shutting Down")


# ── Application Factory ──────────────────────────────────────────────────────

app = FastAPI(
    title="IPL Crowd Management API",
    description=(
        "Automated Real-Time Crowd Dynamics and Agentic Orchestration System "
        "for high-density stadium management. Powered by GCP, Gemini AI, "
        "and the EvacuNet emergency subsystem."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Route Registration ───────────────────────────────────────────────────────

app.include_router(telemetry.router)
app.include_router(gates.router)
app.include_router(evacuation.router)
app.include_router(agents.router)
app.include_router(crowdsource.router)


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Liveness probe for Cloud Run and load balancers."""
    return {
        "status": "healthy",
        "service": "ipl-crowd-management",
        "stadium": settings.stadium_id,
        "version": "1.0.0",
    }


@app.get("/", tags=["system"])
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "service": "IPL Crowd Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
