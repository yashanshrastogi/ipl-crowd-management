"""
EvacuNet — Emergency Evacuation Neural Network
===============================================
A lightweight deep neural network that continuously monitors 15
multi-sensor environmental parameters across stadium zones and predicts
fire / hazard ignition probability BEFORE physical flames present.

Architecture
------------
Input(15) → Linear(64) → ReLU → Dropout(0.3) → Linear(32) → ReLU → Linear(1) → Sigmoid

Loss Function (Binary Cross-Entropy)
-------------------------------------
L(θ) = −(1/N) Σ [yᵢ·log(ŷᵢ) + (1−yᵢ)·log(1−ŷᵢ)]

Where N = sensor zone count, yᵢ ∈ {0,1} actual hazard state,
ŷᵢ = predicted probability.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from app.core.thresholds import EVACUATION_PROBABILITY_THRESHOLD, SENSOR_COUNT
from app.models.evacuation import (
    EvacuationAssessment,
    HazardType,
    SensorVector,
    ZoneHazard,
)

logger = logging.getLogger(__name__)

# ── Model Weights Path (if a pre-trained checkpoint exists) ──────────────────
MODEL_WEIGHTS_PATH = Path(__file__).parent.parent.parent / "weights" / "evacunet.pt"


class EvacuNet(nn.Module):
    """Binary classifier predicting per-zone hazard probability.

    Input:  15 normalised sensor readings
    Output: scalar probability ∈ [0, 1]
    """

    def __init__(self) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(SENSOR_COUNT, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass: sensor vector → hazard probability."""
        return self.network(x)


# ── Module-level model instance ──────────────────────────────────────────────

_model: EvacuNet | None = None


def _get_model() -> EvacuNet:
    """Lazy-load the EvacuNet model (with optional pre-trained weights)."""
    global _model  # noqa: PLW0603
    if _model is None:
        _model = EvacuNet()
        if MODEL_WEIGHTS_PATH.exists():
            _model.load_state_dict(torch.load(MODEL_WEIGHTS_PATH, map_location="cpu", weights_only=True))
            logger.info("EvacuNet weights loaded from %s", MODEL_WEIGHTS_PATH)
        else:
            logger.warning(
                "No pre-trained weights found at %s — using random initialisation. "
                "Predictions will be unreliable until trained.",
                MODEL_WEIGHTS_PATH,
            )
        _model.eval()
    return _model


# ── Normalisation constants (min–max ranges for each sensor channel) ─────────

SENSOR_RANGES = {
    "temperature": (0.0, 80.0),       # °C
    "humidity": (0.0, 100.0),          # %RH
    "tvoc": (0.0, 5000.0),            # ppb
    "co2": (300.0, 10000.0),          # ppm
    "pm25": (0.0, 500.0),             # µg/m³
    "pm10": (0.0, 600.0),             # µg/m³
    "noise_level": (0.0, 140.0),      # dB
    "wind_speed": (0.0, 50.0),        # m/s
    "light_intensity": (0.0, 100000.0),  # lux
    "smoke_density": (0.0, 1.0),      # obscuration ratio
    "heat_flux": (0.0, 50.0),         # kW/m²
    "oxygen_level": (0.0, 25.0),      # % vol
    "methane": (0.0, 50000.0),        # ppm
    "hydrogen_sulfide": (0.0, 100.0), # ppm
    "structural_vibration": (0.0, 10.0),  # mm/s RMS
}


def _normalise(raw: list[float]) -> list[float]:
    """Min–max normalise each sensor channel to [0, 1]."""
    ranges = list(SENSOR_RANGES.values())
    normalised = []
    for i, val in enumerate(raw):
        lo, hi = ranges[i]
        span = hi - lo
        normalised.append((val - lo) / span if span > 0 else 0.0)
    return normalised


# ── Inference ────────────────────────────────────────────────────────────────


def predict_hazard(sensor_vectors: list[SensorVector], zone_ids: list[str]) -> list[ZoneHazard]:
    """Run EvacuNet inference on sensor readings for each zone.

    Parameters
    ----------
    sensor_vectors : list[SensorVector]
        One SensorVector per zone being assessed.
    zone_ids : list[str]
        Corresponding zone identifiers.

    Returns
    -------
    list[ZoneHazard]
        Per-zone hazard assessments with predicted probabilities.
    """
    model = _get_model()

    # Build input tensor: (N_zones, 15)
    raw_matrix = [sv.to_tensor_list() for sv in sensor_vectors]
    norm_matrix = [_normalise(row) for row in raw_matrix]
    input_tensor = torch.tensor(norm_matrix, dtype=torch.float32)

    with torch.no_grad():
        probabilities = model(input_tensor).squeeze(-1).numpy()

    # Ensure 1-D array even for single zone
    if probabilities.ndim == 0:
        probabilities = np.array([probabilities.item()])

    results: list[ZoneHazard] = []
    for i, zone_id in enumerate(zone_ids):
        prob = float(probabilities[i])
        hazard = ZoneHazard(
            zone_id=zone_id,
            probability=round(prob, 4),
            hazard_type=_classify_hazard(sensor_vectors[i]),
            contributing_sensors=_identify_contributors(sensor_vectors[i]),
            is_critical=prob >= EVACUATION_PROBABILITY_THRESHOLD,
        )
        results.append(hazard)

    return results


def assess_stadium(
    stadium_id: str,
    sensor_vectors: list[SensorVector],
    zone_ids: list[str],
) -> EvacuationAssessment:
    """Full-stadium hazard assessment with evacuation recommendation.

    Parameters
    ----------
    stadium_id : str
        Venue identifier.
    sensor_vectors : list[SensorVector]
        Sensor data per zone.
    zone_ids : list[str]
        Zone identifiers.

    Returns
    -------
    EvacuationAssessment
        Complete assessment including whether to evacuate.
    """
    zone_hazards = predict_hazard(sensor_vectors, zone_ids)
    probabilities = [zh.probability for zh in zone_hazards]
    max_prob = max(probabilities) if probabilities else 0.0
    affected = [zh.zone_id for zh in zone_hazards if zh.is_critical]
    should_evacuate = len(affected) > 0

    message = ""
    if should_evacuate:
        message = (
            f"EMERGENCY: Hazard detected in zones {', '.join(affected)}. "
            "Initiating evacuation protocol. Proceed to nearest emergency exit immediately."
        )

    return EvacuationAssessment(
        stadium_id=stadium_id,
        zones=zone_hazards,
        overall_probability=round(max_prob, 4),
        should_evacuate=should_evacuate,
        affected_zones=affected,
        recommended_exits=_recommend_exits(affected),
        evacuation_message=message,
    )


# ── Helpers ──────────────────────────────────────────────────────────────────


def _classify_hazard(sv: SensorVector) -> HazardType:
    """Heuristic hazard-type classification from raw sensor values."""
    if sv.smoke_density > 0.15 or sv.heat_flux > 10.0:
        return HazardType.FIRE
    if sv.smoke_density > 0.05:
        return HazardType.SMOKE
    if sv.co2 > 5000 or sv.tvoc > 2000 or sv.hydrogen_sulfide > 20:
        return HazardType.TOXIC_GAS
    if sv.structural_vibration > 5.0:
        return HazardType.STRUCTURAL
    return HazardType.UNKNOWN


def _identify_contributors(sv: SensorVector) -> list[str]:
    """Identify which sensor channels are driving high readings."""
    contributors: list[str] = []
    if sv.temperature > 55:
        contributors.append("temperature")
    if sv.smoke_density > 0.05:
        contributors.append("smoke_density")
    if sv.co2 > 5000:
        contributors.append("co2")
    if sv.pm25 > 150:
        contributors.append("pm25")
    if sv.tvoc > 2000:
        contributors.append("tvoc")
    if sv.heat_flux > 10:
        contributors.append("heat_flux")
    if sv.hydrogen_sulfide > 20:
        contributors.append("hydrogen_sulfide")
    if sv.methane > 10000:
        contributors.append("methane")
    if sv.structural_vibration > 5:
        contributors.append("structural_vibration")
    return contributors


def _recommend_exits(affected_zones: list[str]) -> list[str]:
    """Map affected zones to recommended emergency exits.

    In production this would use a graph model of stadium topology.
    For the prototype, we return generic gate assignments.
    """
    # Chinnaswamy Stadium has gates A–H around the perimeter
    all_exits = ["gate_a", "gate_b", "gate_c", "gate_d", "gate_e", "gate_f", "gate_g", "gate_h"]
    if not affected_zones:
        return all_exits
    # Simple heuristic: recommend gates not in affected zone quadrant
    return [g for g in all_exits if g not in affected_zones] or all_exits
