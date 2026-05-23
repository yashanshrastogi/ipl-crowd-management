"""
Centralised threshold constants and enumerations for crowd safety classification.
All values derived from empirical pedestrian dynamics research (Fruin, Weidmann).
"""

from __future__ import annotations

from enum import Enum

# ── Pedestrian Physics Constants ──────────────────────────────────────────────

V_MAX: float = 1.34
"""Free-flow walking velocity (m/s) — unimpeded pedestrian speed."""

A_FOOTPRINT: float = 0.26
"""Pedestrian area footprint parameter (m²/ped) — body ellipse approximation."""

# ── Density Thresholds (ped/m²) ──────────────────────────────────────────────

DENSITY_NORMAL_MAX: float = 0.5
"""Comfortable spacing — free movement in all directions."""

DENSITY_ELEVATED_MAX: float = 1.0
"""Noticeable crowding — restricted lateral movement."""

DENSITY_WARNING: float = 1.5
"""Rapid velocity decay onset — compressive shockwave flags triggered."""

DENSITY_CRITICAL: float = 4.0
"""Gridlock state — v→0, extreme danger of compressive asphyxia."""

# ── Wait Time Thresholds (minutes) ───────────────────────────────────────────

WAIT_CLEAR_MAX: float = 5.0
"""Green gate status — acceptable wait."""

WAIT_DELAYED_MAX: float = 15.0
"""Yellow gate status — elevated but manageable."""
# Above 15 min → Red / BLOCKED

# ── Asymmetrical Loading ─────────────────────────────────────────────────────

ASYMMETRIC_LOAD_RATIO: float = 2.0
"""If one gate's wait time exceeds another by this factor, flag imbalance."""

# ── EvacuNet Thresholds ──────────────────────────────────────────────────────

EVACUATION_PROBABILITY_THRESHOLD: float = 0.85
"""Minimum predicted hazard probability to trigger evacuation protocol."""

SENSOR_COUNT: int = 15
"""Number of environmental sensor channels fed to EvacuNet."""

# ── Environmental Alarm Limits ───────────────────────────────────────────────

TEMP_ALARM_C: float = 55.0
CO2_ALARM_PPM: float = 5000.0
PM25_ALARM_UG: float = 150.0
PM10_ALARM_UG: float = 250.0
TVOC_ALARM_PPB: float = 2000.0
SMOKE_ALARM_OBSCURATION: float = 0.3


class RiskLevel(str, Enum):
    """Graduated crowd risk classification."""

    NORMAL = "NORMAL"
    ELEVATED = "ELEVATED"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class GateStatus(str, Enum):
    """Dashboard gate colour mapping."""

    CLEAR = "CLEAR"
    DELAYED = "DELAYED"
    BLOCKED = "BLOCKED"


class EvacuationState(str, Enum):
    """Stadium-wide evacuation protocol state machine."""

    STANDBY = "STANDBY"
    ALERT = "ALERT"
    EVACUATING = "EVACUATING"
    ALL_CLEAR = "ALL_CLEAR"
