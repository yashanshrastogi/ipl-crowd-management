/**
 * Client-side crowd physics calculations.
 * Mirrors backend/app/core/crowd_physics.py for local UI computation.
 */

import {
  V_MAX,
  A_FOOTPRINT,
  DENSITY_NORMAL_MAX,
  DENSITY_ELEVATED_MAX,
  DENSITY_WARNING,
  DENSITY_CRITICAL,
} from './constants';

/**
 * Non-linear velocity function: v(ρ) = v_max · (1 − a·ρ)
 * @param {number} density - Crowd density in ped/m²
 * @returns {number} Walking velocity in m/s (clamped ≥ 0)
 */
export function calculateVelocity(density) {
  const v = V_MAX * (1.0 - A_FOOTPRINT * density);
  return Math.max(v, 0);
}

/**
 * Pedestrian flow rate: Q = ρ · v(ρ) · Wₑ
 * @param {number} density - Crowd density in ped/m²
 * @param {number} effectiveWidth - Passage width in metres
 * @returns {number} Flow rate in ped/s
 */
export function calculateFlowRate(density, effectiveWidth = 3.0) {
  const v = calculateVelocity(density);
  return density * v * effectiveWidth;
}

/**
 * Classify density into a risk level.
 * @param {number} density - ped/m²
 * @returns {'NORMAL'|'ELEVATED'|'WARNING'|'CRITICAL'}
 */
export function assessDensityRisk(density) {
  if (density <= DENSITY_NORMAL_MAX) return 'NORMAL';
  if (density <= DENSITY_ELEVATED_MAX) return 'ELEVATED';
  if (density <= DENSITY_WARNING) return 'WARNING';
  return 'CRITICAL';
}

/**
 * Get the density as a percentage of the critical threshold.
 * Used to drive gauge fill levels.
 * @param {number} density
 * @returns {number} 0–100 percentage
 */
export function densityToPercent(density) {
  return Math.min((density / DENSITY_CRITICAL) * 100, 100);
}

/**
 * Check if gridlock state has been reached (ρ ≥ 4.0).
 * @param {number} density
 * @returns {boolean}
 */
export function isGridlock(density) {
  return density >= DENSITY_CRITICAL;
}
