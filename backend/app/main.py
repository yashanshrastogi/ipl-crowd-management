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

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import settings
from app.routes import agents, crowdsource, evacuation, gates, telemetry

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Security Headers Middleware (V-12) ────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard security response headers to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


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

    # ── V-04: Startup validation ──────────────────────────────────────────
    if settings.app_env == "production":
        if not settings.admin_api_key:
            raise RuntimeError(
                "ADMIN_API_KEY must be set in production. "
                "Set the ADMIN_API_KEY environment variable."
            )
        if settings.admin_api_key in ("supersecret-admin-key", "changeme", "admin"):
            raise RuntimeError(
                "Insecure default ADMIN_API_KEY detected. "
                "Set a strong, unique key via the ADMIN_API_KEY environment variable."
            )

    # ── V-11: CORS wildcard + credentials guard ──────────────────────────
    if "*" in settings.cors_origin_list and settings.app_env == "production":
        raise RuntimeError(
            "Wildcard CORS origin ('*') with credentials is not allowed in production. "
            "Set explicit CORS_ORIGINS."
        )

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

# V-25: Disable OpenAPI docs in production
_docs_url = "/docs" if settings.app_env != "production" else None
_redoc_url = "/redoc" if settings.app_env != "production" else None
_openapi_url = "/openapi.json" if settings.app_env != "production" else None

app = FastAPI(
    title="IPL Crowd Management API",
    description=(
        "Automated Real-Time Crowd Dynamics and Agentic Orchestration System "
        "for high-density stadium management. Powered by GCP, Gemini AI, "
        "and the EvacuNet emergency subsystem."
    ),
    version="1.0.0",
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
    lifespan=lifespan,
)

# ── Security Headers (V-12) ──────────────────────────────────────────────────

app.add_middleware(SecurityHeadersMiddleware)

# ── CORS (V-11: restricted methods/headers) ──────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Only methods actually used
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
    max_age=3600,
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
        "docs": "/docs" if _docs_url else "disabled",
        "health": "/health",
    }
