"""
Pedestrian Routing Sub-Agent
============================
Interacts with the Google Maps Routes API using pedestrian travel mode
(WALK) to generate walking coordinates that circumvent dense bottleneck
corridors.  Pushes updated routes to Firestore for client consumption.
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from app.services import firestore_service, maps_service

logger = logging.getLogger(__name__)

# ── Chinnaswamy Stadium Gate Coordinates ──────────────────────────────────────
# Approximate real-world coordinates for each entry gate
GATE_COORDINATES: dict[str, dict[str, float]] = {
    "gate_a": {"lat": 12.9792, "lng": 77.5990},
    "gate_b": {"lat": 12.9795, "lng": 77.5998},
    "gate_c": {"lat": 12.9790, "lng": 77.6003},
    "gate_d": {"lat": 12.9785, "lng": 77.6002},
    "gate_e": {"lat": 12.9782, "lng": 77.5996},
    "gate_f": {"lat": 12.9783, "lng": 77.5989},
    "gate_g": {"lat": 12.9786, "lng": 77.5985},
    "gate_h": {"lat": 12.9790, "lng": 77.5986},
}


def compute_alternative_routes(
    from_gate_id: str,
    to_gate_id: str,
) -> dict[str, Any]:
    """Compute walking routes between two gates, avoiding congestion.

    Parameters
    ----------
    from_gate_id : str
        Origin gate identifier.
    to_gate_id : str
        Destination gate identifier.

    Returns
    -------
    dict
        Route options with duration, distance, and polyline.
    """
    origin = GATE_COORDINATES.get(from_gate_id)
    dest = GATE_COORDINATES.get(to_gate_id)

    if not origin or not dest:
        return {
            "error": f"Unknown gate IDs: {from_gate_id} or {to_gate_id}",
            "available_gates": list(GATE_COORDINATES.keys()),
        }

    route = maps_service.compute_pedestrian_route(
        origin["lat"], origin["lng"],
        dest["lat"], dest["lng"],
    )

    return {
        "from_gate": from_gate_id,
        "to_gate": to_gate_id,
        **route,
    }


def find_best_alternative_gate(
    congested_gate_id: str,
    stadium_id: str | None = None,
) -> dict[str, Any]:
    """Find the best alternative gate and route for crowd redirection.

    1. Reads all gate statuses from Firestore
    2. Selects the gate with lowest wait time / density
    3. Computes a pedestrian route from the congested gate to the alternative

    Parameters
    ----------
    congested_gate_id : str
        The overloaded gate to redirect away from.
    stadium_id : str, optional
        Stadium identifier (defaults to configured stadium).

    Returns
    -------
    dict
        Best alternative gate info and walking route.
    """
    sid = stadium_id or settings.stadium_id
    gates = firestore_service.get_all_gates(sid)

    if not gates:
        return {"error": "No gate data available"}

    # Sort by wait time, exclude the congested gate
    candidates = [
        g for g in gates
        if g.get("gate_id") != congested_gate_id
    ]
    candidates.sort(key=lambda g: (g.get("wait_time_minutes", 999), g.get("density", 999)))

    if not candidates:
        return {"error": "No alternative gates available"}

    best = candidates[0]
    best_gate_id = best["gate_id"]

    # Compute walking route
    route = compute_alternative_routes(congested_gate_id, best_gate_id)

    result = {
        "congested_gate": congested_gate_id,
        "recommended_gate": best_gate_id,
        "recommended_wait_time": best.get("wait_time_minutes", 0),
        "recommended_density": best.get("density", 0),
        "route": route,
    }

    # Push route update to Firestore for client consumption
    try:
        firestore_service.update_gate_status(
            sid,
            congested_gate_id,
            {
                "redirect_to": best_gate_id,
                "redirect_route": route,
                "signage_message": (
                    f"Gate busy — walk to {best_gate_id.upper()} "
                    f"({route.get('routes', [{}])[0].get('duration', 'N/A')}). "
                    "Follow pedestrian markers."
                ),
            },
        )
    except Exception:
        logger.exception("Failed to push route update to Firestore")

    return result


async def reroute_crowd(
    congested_gate_id: str,
    stadium_id: str | None = None,
) -> dict[str, Any]:
    """High-level routing action: find best alternative and push updates.

    This is the main entry point called by the orchestrator agent.
    """
    return find_best_alternative_gate(congested_gate_id, stadium_id)
