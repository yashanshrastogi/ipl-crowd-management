/**
 * DensityGauge — Animated radial SVG gauge showing real-time crowd density.
 *
 * Color transitions: green → cyan → amber → red based on density thresholds.
 * Includes numerical readout with units (ped/m²).
 */

import { useMemo } from 'react';
import { densityToPercent, assessDensityRisk } from '../utils/crowdPhysics';
import { RISK_LEVELS, DENSITY_CRITICAL } from '../utils/constants';

const RADIUS = 54;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const STROKE_WIDTH = 10;

export default function DensityGauge({
  density = 0,
  label = 'Crowd Density',
  size = 160,
}) {
  const percent = densityToPercent(density);
  const risk = assessDensityRisk(density);
  const riskInfo = RISK_LEVELS[risk];

  const dashOffset = useMemo(
    () => CIRCUMFERENCE - (percent / 100) * CIRCUMFERENCE,
    [percent],
  );

  const gaugeColor = riskInfo.color;

  return (
    <div className="density-gauge" id="density-gauge">
      <p className="gauge-label">{label}</p>

      <div className="gauge-ring-container" style={{ width: size, height: size }}>
        <svg
          viewBox="0 0 128 128"
          width={size}
          height={size}
          style={{ transform: 'rotate(-90deg)' }}
        >
          {/* Background track */}
          <circle
            cx="64"
            cy="64"
            r={RADIUS}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth={STROKE_WIDTH}
          />
          {/* Animated fill */}
          <circle
            cx="64"
            cy="64"
            r={RADIUS}
            className="gauge-ring"
            stroke={gaugeColor}
            strokeWidth={STROKE_WIDTH}
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={dashOffset}
            style={{
              filter: `drop-shadow(0 0 6px ${gaugeColor}60)`,
            }}
          />
        </svg>

        {/* Center readout */}
        <div className="gauge-center">
          <span className="gauge-value font-mono" style={{ color: gaugeColor }}>
            {density.toFixed(2)}
          </span>
          <span className="gauge-unit">ped/m²</span>
        </div>
      </div>

      <div className="gauge-risk-badge">
        <span
          className="badge"
          style={{
            background: riskInfo.bg,
            color: riskInfo.color,
            border: `1px solid ${riskInfo.color}40`,
          }}
        >
          <span
            className="status-dot"
            style={{
              background: riskInfo.color,
              width: 8,
              height: 8,
            }}
          />
          {riskInfo.label}
        </span>
      </div>

      <div className="gauge-capacity-bar">
        <div className="capacity-label">
          <span>Capacity</span>
          <span className="font-mono">{Math.round(percent)}%</span>
        </div>
        <div className="capacity-track">
          <div
            className="capacity-fill"
            style={{
              width: `${percent}%`,
              background: gaugeColor,
              boxShadow: `0 0 8px ${gaugeColor}40`,
            }}
          />
        </div>
      </div>
    </div>
  );
}
