"""
Pydantic schemas for the EvacuNet emergency evacuation subsystem.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class HazardType(str, Enum):
    """Classification of detected hazard source."""

    FIRE = "FIRE"
    SMOKE = "SMOKE"
    TOXIC_GAS = "TOXIC_GAS"
    STRUCTURAL = "STRUCTURAL"
    CROWD_CRUSH = "CROWD_CRUSH"
    UNKNOWN = "UNKNOWN"


class ZoneHazard(BaseModel):
    """Hazard assessment for a single stadium zone."""

    zone_id: str
    probability: float = Field(..., ge=0.0, le=1.0, description="Predicted hazard probability [0,1]")
    hazard_type: HazardType = HazardType.UNKNOWN
    contributing_sensors: list[str] = Field(default_factory=list)
    is_critical: bool = False


class EvacuationAssessment(BaseModel):
    """Complete EvacuNet assessment across all zones."""

    stadium_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    zones: list[ZoneHazard] = Field(default_factory=list)
    overall_probability: float = Field(0.0, ge=0.0, le=1.0)
    should_evacuate: bool = False
    affected_zones: list[str] = Field(default_factory=list)
    recommended_exits: list[str] = Field(default_factory=list)
    evacuation_message: str = ""


class EvacuationTrigger(BaseModel):
    """Request payload to force an evacuation protocol."""

    stadium_id: str
    reason: str
    affected_zones: list[str] = Field(default_factory=list)
    override_authority: str = "system"  # "system" | "security_chief" | "fire_marshal"


class SensorVector(BaseModel):
    """15-dimensional environmental sensor vector for EvacuNet input."""

    temperature: float = 0.0
    humidity: float = 0.0
    tvoc: float = 0.0
    co2: float = 0.0
    pm25: float = 0.0
    pm10: float = 0.0
    noise_level: float = 0.0
    wind_speed: float = 0.0
    light_intensity: float = 0.0
    smoke_density: float = 0.0
    heat_flux: float = 0.0
    oxygen_level: float = 20.9  # Normal atmospheric O₂
    methane: float = 0.0
    hydrogen_sulfide: float = 0.0
    structural_vibration: float = 0.0

    def to_tensor_list(self) -> list[float]:
        """Convert to ordered list for PyTorch tensor construction."""
        return [
            self.temperature,
            self.humidity,
            self.tvoc,
            self.co2,
            self.pm25,
            self.pm10,
            self.noise_level,
            self.wind_speed,
            self.light_intensity,
            self.smoke_density,
            self.heat_flux,
            self.oxygen_level,
            self.methane,
            self.hydrogen_sulfide,
            self.structural_vibration,
        ]
