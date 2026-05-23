"""
Maps Service
============
Integration with the Google Maps Routes API for pedestrian routing.
Uses strict X-Goog-FieldMask headers to minimize JSON payload overhead
on client devices as required by the enterprise spec.

Travel mode is always WALK.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

ROUTES_API_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

# Strict field mask — only request what we need
FIELD_MASK = "routes.duration,routes.distanceMeters,routes.polyline"


def compute_pedestrian_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> dict[str, Any]:
    """Compute a walking route between two coordinates.

    Parameters
    ----------
    origin_lat, origin_lng : float
        Origin coordinates (latitude, longitude).
    dest_lat, dest_lng : float
        Destination coordinates.

    Returns
    -------
    dict
        Route details including duration, distance, and encoded polyline.
        Also includes the mandatory beta warning for pedestrian routes.
    """
    api_key = settings.google_maps_api_key
    if not api_key:
        logger.warning("GOOGLE_MAPS_API_KEY not set — returning mock route")
        return _mock_route(origin_lat, origin_lng, dest_lat, dest_lng)

    request_body = {
        "origin": {
            "location": {
                "latLng": {"latitude": origin_lat, "longitude": origin_lng}
            }
        },
        "destination": {
            "location": {
                "latLng": {"latitude": dest_lat, "longitude": dest_lng}
            }
        },
        "travelMode": "WALK",
        "computeAlternativeRoutes": True,
        "languageCode": "en-US",
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(ROUTES_API_URL, json=request_body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("Routes API HTTP error: %s — %s", exc.response.status_code, exc.response.text)
        return {"error": str(exc), "routes": []}
    except Exception as exc:
        logger.exception("Routes API call failed")
        return {"error": str(exc), "routes": []}

    routes = data.get("routes", [])
    return {
        "routes": [
            {
                "duration": r.get("duration", "0s"),
                "distance_meters": r.get("distanceMeters", 0),
                "polyline": r.get("polyline", {}).get("encodedPolyline", ""),
            }
            for r in routes
        ],
        "beta_warning": (
            "Walking paths may lack completed sidewalks or pedestrian crossings"
        ),
        "travel_mode": "WALK",
    }


def _mock_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> dict[str, Any]:
    """Return a plausible mock route for development without a live API key."""
    return {
        "routes": [
            {
                "duration": "480s",
                "distance_meters": 620,
                "polyline": "",
            }
        ],
        "beta_warning": (
            "Walking paths may lack completed sidewalks or pedestrian crossings"
        ),
        "travel_mode": "WALK",
        "mock": True,
    }
