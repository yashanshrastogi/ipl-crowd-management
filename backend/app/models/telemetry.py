"""
Pydantic schemas for multi-sensor environmental telemetry payloads.
Covers the 15 key parameters monitored by the EvacuNet subsystem.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SensorType(str, Enum):
    """Enumeration of all monitored environmental sensor channels."""

    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    TVOC = "tvoc"
    CO2 = "co2"
    PM25 = "pm25"
    PM10 = "pm10"
    NOISE_LEVEL = "noise_level"
    WIND_SPEED = "wind_speed"
    LIGHT_INTENSITY = "light_intensity"
    SMOKE_DENSITY = "smoke_density"
    HEAT_FLUX = "heat_flux"
    OXYGEN_LEVEL = "oxygen_level"
    METHANE = "methane"
    HYDROGEN_SULFIDE = "hydrogen_sulfide"
    STRUCTURAL_VIBRATION = "structural_vibration"


class SensorReading(BaseModel):
    """A single sensor measurement from a specific zone."""

    sensor_type: SensorType
    value: float = Field(..., description="Raw sensor value in native units")
    unit: str = Field(..., description="SI unit string (e.g. '°C', 'ppm', 'µg/m³')")
    zone_id: str = Field(..., description="Stadium zone identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TelemetryPayload(BaseModel):
    """Batch telemetry payload ingested from IoT gateway or Pub/Sub push."""

    stadium_id: str
    gate_id: str | None = None
    zone_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    readings: list[SensorReading] = Field(default_factory=list)

    # Crowd metrics (optional — may arrive from camera CV pipeline)
    crowd_density: float | None = Field(
        None, ge=0, description="Local crowd density (ped/m²)"
    )
    estimated_count: int | None = Field(
        None, ge=0, description="Estimated headcount in zone"
    )
    mean_velocity: float | None = Field(
        None, ge=0, description="Mean walking velocity (m/s)"
    )


class PubSubMessage(BaseModel):
    """Wrapper matching the Google Cloud Pub/Sub push message envelope."""

    message: PubSubMessageBody
    subscription: str


class PubSubMessageBody(BaseModel):
    """Inner Pub/Sub message containing base64-encoded data."""

    data: str = Field(..., description="Base64-encoded JSON telemetry payload")
    message_id: str
    publish_time: datetime
    attributes: dict[str, str] = Field(default_factory=dict)
