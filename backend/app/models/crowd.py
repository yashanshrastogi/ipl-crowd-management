"""
Pydantic schemas for crowd flow metrics, gate status, and real-time snapshots.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Crowd density risk classification."""

    NORMAL = "NORMAL"
    ELEVATED = "ELEVATED"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class GateStatus(str, Enum):
    """Visual gate status for dashboard markers."""

    CLEAR = "CLEAR"       # Green — wait < 5 min
    DELAYED = "DELAYED"   # Yellow — wait 5–15 min
    BLOCKED = "BLOCKED"   # Red — wait > 15 min or critical density


class StrictProtocol(BaseModel):
    """Strict Protocol broadcast payload for gate security."""

    gate_id: str
    active: bool = False
    banned_items: list[str] = Field(
        default_factory=lambda: ["bags", "coins", "bottles", "umbrellas"]
    )
    message: str = "Prepare credentials. Remove banned items before queuing."
    activated_at: datetime | None = None


class GateMetrics(BaseModel):
    """Live metrics for a single entry gate."""

    gate_id: str
    gate_name: str = ""
    latitude: float = 0.0
    longitude: float = 0.0

    # Crowd physics
    density: float = Field(0.0, ge=0, description="ped/m²")
    velocity: float = Field(0.0, ge=0, description="m/s")
    flow_rate: float = Field(0.0, ge=0, description="ped/s")
    effective_width: float = Field(3.0, gt=0, description="Passage width in metres")

    # Operational
    wait_time_minutes: float = Field(0.0, ge=0)
    throughput_per_minute: float = Field(0.0, ge=0)
    queue_length: int = Field(0, ge=0)

    # Status
    risk_level: RiskLevel = RiskLevel.NORMAL
    gate_status: GateStatus = GateStatus.CLEAR
    strict_protocol: StrictProtocol | None = None

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CrowdFlowSnapshot(BaseModel):
    """Aggregate snapshot of all gates at a point in time."""

    stadium_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    gates: list[GateMetrics] = Field(default_factory=list)
    overall_risk: RiskLevel = RiskLevel.NORMAL
    total_inside: int = 0
    venue_capacity: int = 40_000  # Chinnaswamy Stadium capacity


class SignageUpdate(BaseModel):
    """Request payload for updating dynamic LED signage at a gate."""

    gate_id: str
    message: str
    priority: str = "normal"  # "normal" | "high" | "emergency"


class CrowdsourcedReport(BaseModel):
    """Spectator-submitted field report."""

    report_id: str = ""
    reporter_type: str = "spectator"  # "spectator" | "security" | "system"
    message: str
    zone_id: str = ""
    gate_id: str = ""
    severity: str = "info"  # "info" | "warning" | "critical"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
