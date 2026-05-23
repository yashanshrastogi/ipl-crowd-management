"""
Gate & Security Sub-Agent
=========================
Monitors entry throughput and detects Asymmetrical Gate Loading.
When wait times spike due to latency at checkpoints, dynamically
triggers "Strict Protocol" broadcasts advising oncoming crowds to
prepare credentials and remove banned items.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.thresholds import (
    ASYMMETRIC_LOAD_RATIO,
    DENSITY_WARNING,
    WAIT_DELAYED_MAX,
)
from app.services import firestore_service
from app.config import settings

logger = logging.getLogger(__name__)


def analyse_gate_loading(stadium_id: str) -> dict[str, Any]:
    """Detect asymmetrical gate loading and trigger Strict Protocol where needed.

    Asymmetrical loading is flagged when one gate's wait time exceeds
    another's by a factor of ASYMMETRIC_LOAD_RATIO (2×).

    Returns
    -------
    dict
        Analysis results including flagged gates and actions taken.
    """
    gates = firestore_service.get_all_gates(stadium_id)
    if not gates:
        return {"stadium_id": stadium_id, "status": "no_gates_found", "actions": []}

    wait_times = {g["gate_id"]: g.get("wait_time_minutes", 0) for g in gates}
    densities = {g["gate_id"]: g.get("density", 0) for g in gates}

    min_wait = min(wait_times.values()) if wait_times else 0
    actions: list[dict[str, Any]] = []
    flagged_gates: list[str] = []

    for gate_id, wait in wait_times.items():
        density = densities.get(gate_id, 0)
        is_asymmetric = (
            min_wait > 0 and wait / min_wait >= ASYMMETRIC_LOAD_RATIO
        )
        is_high_density = density >= DENSITY_WARNING
        is_long_wait = wait > WAIT_DELAYED_MAX

        if is_asymmetric or is_high_density or is_long_wait:
            flagged_gates.append(gate_id)

            # Activate Strict Protocol
            try:
                firestore_service.update_strict_protocol(
                    stadium_id,
                    gate_id,
                    active=True,
                    message=(
                        f"STRICT PROTOCOL ACTIVE — Gate {gate_id.upper()}: "
                        "No bags, no coins, no bottles. "
                        "Have your ticket and ID ready. "
                        "Remove metal items before screening."
                    ),
                )
                actions.append({
                    "gate_id": gate_id,
                    "action": "STRICT_PROTOCOL_ACTIVATED",
                    "reason": (
                        "asymmetric_loading" if is_asymmetric
                        else "high_density" if is_high_density
                        else "long_wait"
                    ),
                    "wait_time": wait,
                    "density": density,
                })
            except Exception:
                logger.exception("Failed to activate Strict Protocol at %s", gate_id)

    # Deactivate Strict Protocol on clear gates
    for gate_id in wait_times:
        if gate_id not in flagged_gates:
            try:
                firestore_service.update_strict_protocol(
                    stadium_id, gate_id, active=False,
                )
            except Exception:
                logger.exception("Failed to deactivate Strict Protocol at %s", gate_id)

    return {
        "stadium_id": stadium_id,
        "total_gates": len(gates),
        "flagged_gates": flagged_gates,
        "actions": actions,
        "min_wait": min_wait,
        "wait_times": wait_times,
    }


def get_underutilised_gates(stadium_id: str, max_count: int = 3) -> list[dict[str, Any]]:
    """Identify the least-loaded gates for crowd redirection.

    Returns gates sorted by wait time (ascending), capped at max_count.
    """
    gates = firestore_service.get_all_gates(stadium_id)
    sorted_gates = sorted(gates, key=lambda g: g.get("wait_time_minutes", 0))
    return sorted_gates[:max_count]


async def run_security_scan(stadium_id: str | None = None) -> dict[str, Any]:
    """Execute a full security scan cycle.

    1. Analyse gate loading for asymmetry
    2. Flag and activate Strict Protocol where needed
    3. Identify underutilised gates for redirection
    """
    sid = stadium_id or settings.stadium_id
    analysis = analyse_gate_loading(sid)
    underutilised = get_underutilised_gates(sid)

    return {
        **analysis,
        "underutilised_gates": [
            {"gate_id": g["gate_id"], "wait_time": g.get("wait_time_minutes", 0)}
            for g in underutilised
        ],
    }
