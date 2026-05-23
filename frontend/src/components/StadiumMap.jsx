/**
 * StadiumMap — Interactive map centered on M. Chinnaswamy Stadium.
 *
 * Uses a lightweight embedded map approach. For production,
 * integrate `@vis.gl/react-google-maps` with a real API key.
 * Currently renders a stylized SVG stadium map with gate markers
 * as a self-contained fallback (no API key required).
 */

import { useState } from 'react';
import { STADIUM, GATES, GATE_STATUSES, WAIT_CLEAR_MAX, WAIT_DELAYED_MAX, MAPS_BETA_WARNING } from '../utils/constants';

function getGateStatus(waitTime) {
  if (waitTime <= WAIT_CLEAR_MAX) return 'CLEAR';
  if (waitTime <= WAIT_DELAYED_MAX) return 'DELAYED';
  return 'BLOCKED';
}

// Gate positions mapped to SVG coordinates around an ellipse
const GATE_POSITIONS = [
  { angle: 90,   x: 200, y: 40  },  // Gate A — North
  { angle: 45,   x: 320, y: 70  },  // Gate B — North-East
  { angle: 0,    x: 360, y: 170 },  // Gate C — East
  { angle: -45,  x: 320, y: 270 },  // Gate D — South-East
  { angle: -90,  x: 200, y: 300 },  // Gate E — South
  { angle: -135, x: 80,  y: 270 },  // Gate F — South-West
  { angle: 180,  x: 40,  y: 170 },  // Gate G — West
  { angle: 135,  x: 80,  y: 70  },  // Gate H — North-West
];

export default function StadiumMap({ gateMetrics = {} }) {
  const [selectedGate, setSelectedGate] = useState(null);

  return (
    <div className="stadium-map-container" id="stadium-map">
      <div className="map-header">
        <h3 className="map-title">
          <span className="map-icon">🗺️</span>
          {STADIUM.name}
        </h3>
        <span className="map-coords font-mono">
          {STADIUM.center.lat.toFixed(4)}°N, {STADIUM.center.lng.toFixed(4)}°E
        </span>
      </div>

      <div className="map-canvas">
        <svg viewBox="0 0 400 340" className="stadium-svg">
          {/* Stadium ellipse */}
          <defs>
            <radialGradient id="fieldGrad" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="rgba(16,185,129,0.15)" />
              <stop offset="100%" stopColor="rgba(16,185,129,0.03)" />
            </radialGradient>
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>

          {/* Outer stadium ring */}
          <ellipse
            cx="200" cy="170" rx="175" ry="140"
            fill="none"
            stroke="rgba(255,255,255,0.08)"
            strokeWidth="30"
          />
          {/* Inner field */}
          <ellipse
            cx="200" cy="170" rx="120" ry="90"
            fill="url(#fieldGrad)"
            stroke="rgba(16,185,129,0.2)"
            strokeWidth="1"
          />
          {/* Pitch rectangle */}
          <rect
            x="175" y="145" width="50" height="50" rx="2"
            fill="none"
            stroke="rgba(16,185,129,0.3)"
            strokeWidth="0.5"
          />

          {/* Gate markers */}
          {GATES.map((gate, i) => {
            const pos = GATE_POSITIONS[i];
            const metrics = gateMetrics[gate.id] || {};
            const status = getGateStatus(metrics.wait_time || 0);
            const statusInfo = GATE_STATUSES[status];
            const isSelected = selectedGate === gate.id;

            return (
              <g
                key={gate.id}
                className="gate-marker-group"
                onClick={() => setSelectedGate(isSelected ? null : gate.id)}
                style={{ cursor: 'pointer' }}
              >
                {/* Pulse ring */}
                <circle
                  cx={pos.x} cy={pos.y} r={isSelected ? 18 : 14}
                  fill={`${statusInfo.color}20`}
                  stroke={statusInfo.color}
                  strokeWidth={isSelected ? 2 : 1}
                  filter={status === 'BLOCKED' ? 'url(#glow)' : undefined}
                  style={{
                    animation: status === 'BLOCKED'
                      ? 'pulse-ring 2s ease-out infinite'
                      : undefined,
                  }}
                />
                {/* Center dot */}
                <circle
                  cx={pos.x} cy={pos.y} r="5"
                  fill={statusInfo.color}
                />
                {/* Label */}
                <text
                  x={pos.x}
                  y={pos.y - 20}
                  textAnchor="middle"
                  fill="var(--text-secondary)"
                  fontSize="10"
                  fontFamily="var(--font-sans)"
                  fontWeight="600"
                >
                  {gate.name}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Selected gate detail */}
      {selectedGate && (
        <div className="map-gate-detail animate-fade-in">
          {(() => {
            const gate = GATES.find((g) => g.id === selectedGate);
            const m = gateMetrics[selectedGate] || {};
            const status = getGateStatus(m.wait_time || 0);
            const statusInfo = GATE_STATUSES[status];
            return (
              <>
                <div className="detail-header">
                  <span style={{ color: statusInfo.color }}>●</span>
                  <strong>{gate.name}</strong>
                  <span className="gate-section">{gate.section}</span>
                </div>
                <div className="detail-stats font-mono">
                  <span>ρ {(m.density || 0).toFixed(2)} ped/m²</span>
                  <span>⏱ {(m.wait_time || 0).toFixed(0)} min</span>
                  <span>↗ {(m.throughput || 0)} ped/min</span>
                </div>
              </>
            );
          })()}
        </div>
      )}

      {/* Beta warning */}
      <p className="map-beta-warning">{MAPS_BETA_WARNING}</p>

      {/* Legend */}
      <div className="map-legend">
        {Object.entries(GATE_STATUSES).map(([key, val]) => (
          <div className="legend-item" key={key}>
            <span className="legend-dot" style={{ background: val.color }} />
            <span>{val.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
