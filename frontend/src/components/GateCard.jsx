/**
 * GateCard — Individual gate status card.
 *
 * Shows gate name, section, current density, wait time, flow rate,
 * and a color-coded status indicator.
 */

import { GATE_STATUSES, RISK_LEVELS, WAIT_CLEAR_MAX, WAIT_DELAYED_MAX } from '../utils/constants';
import { calculateVelocity, calculateFlowRate, assessDensityRisk } from '../utils/crowdPhysics';

/**
 * Derive gate status from wait time.
 */
function getGateStatus(waitTime) {
  if (waitTime <= WAIT_CLEAR_MAX) return 'CLEAR';
  if (waitTime <= WAIT_DELAYED_MAX) return 'DELAYED';
  return 'BLOCKED';
}

export default function GateCard({ gate, metrics = {} }) {
  const {
    density = 0,
    wait_time: waitTime = 0,
    throughput = 0,
    strict_protocol: strictProtocol = false,
  } = metrics;

  const risk = assessDensityRisk(density);
  const riskInfo = RISK_LEVELS[risk];
  const status = getGateStatus(waitTime);
  const statusInfo = GATE_STATUSES[status];
  const velocity = calculateVelocity(density);
  const flowRate = calculateFlowRate(density);

  return (
    <div
      className="gate-card glass-card"
      id={`gate-card-${gate.id}`}
      style={{
        borderLeft: `3px solid ${statusInfo.color}`,
      }}
    >
      <div className="gate-header">
        <div className="gate-name-group">
          <h3 className="gate-name">{gate.name}</h3>
          <span className="gate-section">{gate.section}</span>
        </div>
        <div className="gate-status-group">
          <span
            className={`status-dot status-${status.toLowerCase()}`}
          />
          <span
            className="gate-status-label"
            style={{ color: statusInfo.color }}
          >
            {statusInfo.label}
          </span>
        </div>
      </div>

      {strictProtocol && (
        <div className="gate-strict-banner">
          <span>⚠️ STRICT PROTOCOL ACTIVE</span>
        </div>
      )}

      <div className="gate-metrics-grid">
        <div className="gate-metric">
          <span className="metric-value font-mono" style={{ color: riskInfo.color }}>
            {density.toFixed(2)}
          </span>
          <span className="metric-label">ped/m²</span>
        </div>
        <div className="gate-metric">
          <span className="metric-value font-mono">
            {waitTime.toFixed(0)}
          </span>
          <span className="metric-label">min wait</span>
        </div>
        <div className="gate-metric">
          <span className="metric-value font-mono">
            {velocity.toFixed(2)}
          </span>
          <span className="metric-label">m/s</span>
        </div>
        <div className="gate-metric">
          <span className="metric-value font-mono">
            {flowRate.toFixed(1)}
          </span>
          <span className="metric-label">ped/s</span>
        </div>
      </div>

      <div className="gate-throughput-bar">
        <div className="capacity-label">
          <span>Throughput</span>
          <span className="font-mono">{throughput} ped/min</span>
        </div>
        <div className="capacity-track">
          <div
            className="capacity-fill"
            style={{
              width: `${Math.min((throughput / 120) * 100, 100)}%`,
              background: statusInfo.color,
            }}
          />
        </div>
      </div>
    </div>
  );
}
