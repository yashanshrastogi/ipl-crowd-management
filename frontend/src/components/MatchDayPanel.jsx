/**
 * MatchDayPanel — Environmental metrics dashboard + EvacuNet hazard score.
 *
 * Displays temperature, humidity, CO₂, PM2.5, TVOC, noise level
 * along with the EvacuNet hazard probability gauge.
 */

import { SENSOR_LABELS } from '../utils/constants';

const DEFAULT_SENSORS = {
  temperature: 32,
  humidity: 68,
  co2: 420,
  pm25: 35,
  tvoc: 180,
  noise_level: 78,
};

function getSensorStatus(key, value) {
  const thresholds = {
    temperature: { warn: 38, crit: 42 },
    humidity: { warn: 80, crit: 90 },
    co2: { warn: 800, crit: 1500 },
    pm25: { warn: 55, crit: 150 },
    tvoc: { warn: 500, crit: 1000 },
    noise_level: { warn: 85, crit: 100 },
  };
  const t = thresholds[key];
  if (!t) return 'normal';
  if (value >= t.crit) return 'critical';
  if (value >= t.warn) return 'warning';
  return 'normal';
}

function statusColor(status) {
  return {
    normal: 'var(--accent-green)',
    warning: 'var(--accent-amber)',
    critical: 'var(--accent-red)',
  }[status];
}

export default function MatchDayPanel({
  sensorData = DEFAULT_SENSORS,
  evacunetScore = 0.12,
  transitHubs = [],
}) {
  const hazardPercent = Math.round(evacunetScore * 100);
  const hazardColor =
    evacunetScore >= 0.85
      ? 'var(--accent-red)'
      : evacunetScore >= 0.5
        ? 'var(--accent-amber)'
        : 'var(--accent-green)';

  return (
    <div className="matchday-panel" id="matchday-panel">
      <div className="panel-header">
        <h3>
          <span>📊</span> Match Day Conditions
        </h3>
        <span className="badge badge-green">LIVE</span>
      </div>

      {/* Sensor grid */}
      <div className="sensors-grid">
        {Object.entries(SENSOR_LABELS).map(([key, meta]) => {
          const value = sensorData[key] ?? 0;
          const status = getSensorStatus(key, value);
          const color = statusColor(status);
          return (
            <div className="sensor-card" key={key}>
              <div className="sensor-icon">{meta.icon}</div>
              <div className="sensor-info">
                <span className="sensor-name">{meta.label}</span>
                <span className="sensor-value font-mono" style={{ color }}>
                  {typeof value === 'number' ? value.toFixed(1) : value}
                  <span className="sensor-unit">{meta.unit}</span>
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* EvacuNet hazard bar */}
      <div className="evacunet-section">
        <div className="evacunet-header">
          <span>🧠 EvacuNet Hazard Score</span>
          <span className="font-mono" style={{ color: hazardColor }}>
            {hazardPercent}%
          </span>
        </div>
        <div className="capacity-track">
          <div
            className="capacity-fill"
            style={{
              width: `${hazardPercent}%`,
              background: hazardColor,
              boxShadow: `0 0 8px ${hazardColor}40`,
              transition: 'width 0.8s cubic-bezier(0.4,0,0.2,1)',
            }}
          />
        </div>
        <div className="evacunet-labels">
          <span>Safe</span>
          <span>Caution</span>
          <span>Evacuate</span>
        </div>
      </div>

      {/* Transit hub capacity (if available) */}
      {transitHubs.length > 0 && (
        <div className="transit-section">
          <h4>🚉 Transit Hub Capacity</h4>
          {transitHubs.map((hub) => (
            <div className="transit-hub" key={hub.name}>
              <div className="capacity-label">
                <span>{hub.name}</span>
                <span className="font-mono">{hub.percent}%</span>
              </div>
              <div className="capacity-track">
                <div
                  className="capacity-fill"
                  style={{
                    width: `${hub.percent}%`,
                    background:
                      hub.percent > 85
                        ? 'var(--accent-red)'
                        : hub.percent > 60
                          ? 'var(--accent-amber)'
                          : 'var(--accent-green)',
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
