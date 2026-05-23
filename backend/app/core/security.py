"""
Security dependencies for FastAPI route guards.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.config import settings


async def verify_admin_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Validate that the request includes a valid X-API-Key header."""
    if not settings.admin_api_key:
        # If admin_api_key is empty/disabled, pass validation
        return ""
    if x_api_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header",
        )
    return x_api_key
