/**
 * EvacuNetAlert — Full-screen emergency evacuation overlay.
 *
 * Triggered when EvacuNet hazard probability exceeds threshold (0.85).
 * Cannot be dismissed during active evacuation.
 * Displays evacuation routes, countdown, affected zones.
 */

import { useState, useEffect } from 'react';

export default function EvacuNetAlert(props) {
  return props.active ? <EvacuNetAlertContent {...props} /> : null;
}

function EvacuNetAlertContent({
  active = false,
  hazardScore = 0,
  affectedZones = [],
  evacuationRoutes = [],
  reason = '',
  onAcknowledge,
}) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setElapsedSeconds((seconds) => seconds + 1), 1000);
    return () => clearInterval(timer);
  }, [active]);

  const minutes = Math.floor(elapsedSeconds / 60);
  const seconds = elapsedSeconds % 60;

  return (
    <div className="evacuation-overlay" id="evacuation-overlay">
      <div className="evac-content animate-scale-in">
        <div className="evac-icon-container">
          <span className="evac-icon">🚨</span>
        </div>

        <h1 className="evac-title">EMERGENCY EVACUATION</h1>
        <p className="evac-subtitle">
          EvacuNet has detected a critical hazard — evacuate immediately
        </p>

        {reason && (
          <div className="evac-reason">
            <strong>Reason:</strong> {reason}
          </div>
        )}

        <div className="evac-stats">
          <div className="evac-stat">
            <span className="evac-stat-value font-mono">
              {(hazardScore * 100).toFixed(0)}%
            </span>
            <span className="evac-stat-label">Hazard Score</span>
          </div>
          <div className="evac-stat">
            <span className="evac-stat-value font-mono">
              {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
            </span>
            <span className="evac-stat-label">Elapsed</span>
          </div>
          <div className="evac-stat">
            <span className="evac-stat-value font-mono">
              {affectedZones.length || 'ALL'}
            </span>
            <span className="evac-stat-label">Zones</span>
          </div>
        </div>

        {affectedZones.length > 0 && (
          <div className="evac-zones">
            <h3>Affected Zones</h3>
            <div className="evac-zone-tags">
              {affectedZones.map((zone) => (
                <span key={zone} className="badge badge-red">
                  {zone}
                </span>
              ))}
            </div>
          </div>
        )}

        {evacuationRoutes.length > 0 && (
          <div className="evac-routes">
            <h3>Evacuation Routes</h3>
            {evacuationRoutes.map((route, i) => (
              <div key={i} className="evac-route-item">
                <span className="route-number">{i + 1}</span>
                <div>
                  <strong>{route.from} → {route.to}</strong>
                  <span className="route-detail">
                    {route.distance || '—'} • {route.duration || '—'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="evac-instructions">
          <p>🏃 Stay calm • Follow illuminated exit signs • Do not use elevators</p>
          <p>📱 Emergency: 112 | Stadium Control: +91-80-2225-0000</p>
        </div>

        {onAcknowledge && (
          <button
            className="btn-danger evac-ack-btn"
            onClick={onAcknowledge}
            id="evac-acknowledge"
          >
            Acknowledge — I am proceeding to exit
          </button>
        )}
      </div>
    </div>
  );
}
