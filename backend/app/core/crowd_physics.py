"""
Crowd Physics Engine
====================
Implements the pedestrian fluid-dynamics equations for real-time crowd
flow modelling.  These functions are the mathematical core used by both
the Dataflow pipeline and the FastAPI telemetry processors.

Key equations
-------------
Flow rate:   Q = ρ · v(ρ) · Wₑ
Velocity:    v(ρ) = v_max · (1 − a·ρ)       (clamped to [0, v_max])
"""

from __future__ import annotations

from app.core.thresholds import (
    A_FOOTPRINT,
    DENSITY_CRITICAL,
    DENSITY_ELEVATED_MAX,
    DENSITY_NORMAL_MAX,
    DENSITY_WARNING,
    V_MAX,
    WAIT_CLEAR_MAX,
    WAIT_DELAYED_MAX,
    GateStatus,
    RiskLevel,
)


# ── Velocity ──────────────────────────────────────────────────────────────────


def calculate_velocity(density: float) -> float:
    """Non-linear velocity function v(ρ) = v_max·(1 − a·ρ), clamped ≥ 0.

    Parameters
    ----------
    density : float
        Local crowd density in ped/m².

    Returns
    -------
    float
        Mean walking velocity in m/s.
    """
    v = V_MAX * (1.0 - A_FOOTPRINT * density)
    return max(v, 0.0)


# ── Flow Rate ─────────────────────────────────────────────────────────────────


def calculate_flow_rate(density: float, effective_width: float) -> float:
    """Pedestrian flow rate Q = ρ · v(ρ) · Wₑ.

    Parameters
    ----------
    density : float
        Local crowd density in ped/m².
    effective_width : float
        Passage effective width in metres (adjusted for boundary layers).

    Returns
    -------
    float
        Flow rate in ped/s.
    """
    v = calculate_velocity(density)
    return density * v * effective_width


# ── Risk Assessment ───────────────────────────────────────────────────────────


def assess_density_risk(density: float) -> RiskLevel:
    """Classify density into a graduated risk level.

    Thresholds (ped/m²)
    --------------------
    ≤ 0.5   → NORMAL
    ≤ 1.0   → ELEVATED
    ≤ 1.5   → WARNING   (compressive shockwave flags)
    > 1.5   → CRITICAL  (approaching gridlock / asphyxia risk at ≥ 4.0)
    """
    if density <= DENSITY_NORMAL_MAX:
        return RiskLevel.NORMAL
    if density <= DENSITY_ELEVATED_MAX:
        return RiskLevel.ELEVATED
    if density <= DENSITY_WARNING:
        return RiskLevel.WARNING
    return RiskLevel.CRITICAL


def classify_gate_status(wait_time_minutes: float, density: float) -> GateStatus:
    """Map wait time and density to a colour-coded gate status.

    Green  (CLEAR)   — wait < 5 min and density below warning
    Yellow (DELAYED) — wait 5–15 min
    Red    (BLOCKED) — wait > 15 min or critical density
    """
    if density >= DENSITY_CRITICAL or wait_time_minutes > WAIT_DELAYED_MAX:
        return GateStatus.BLOCKED
    if wait_time_minutes > WAIT_CLEAR_MAX or density >= DENSITY_WARNING:
        return GateStatus.DELAYED
    return GateStatus.CLEAR


def is_gridlock(density: float) -> bool:
    """Return True when density reaches the gridlock threshold (≥ 4.0 ped/m²)."""
    return density >= DENSITY_CRITICAL


def compute_gate_metrics(
    density: float,
    effective_width: float,
    wait_time_minutes: float,
) -> dict:
    """Convenience function computing all derived physics for a gate.

    Returns a dict with velocity, flow_rate, risk_level, gate_status, and
    a gridlock boolean.
    """
    velocity = calculate_velocity(density)
    flow_rate = calculate_flow_rate(density, effective_width)
    risk = assess_density_risk(density)
    status = classify_gate_status(wait_time_minutes, density)

    return {
        "velocity": round(velocity, 4),
        "flow_rate": round(flow_rate, 4),
        "risk_level": risk.value,
        "gate_status": status.value,
        "gridlock": is_gridlock(density),
    }
