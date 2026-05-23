/**
 * Navbar — Top navigation bar with live status indicator.
 *
 * Displays the stadium name, live match badge, current time,
 * and connection health dot.
 */

import { useState, useEffect } from 'react';
import { STADIUM } from '../utils/constants';

export default function Navbar({ connectionStatus = 'connected' }) {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const statusColors = {
    connected: 'var(--accent-green)',
    reconnecting: 'var(--accent-amber)',
    disconnected: 'var(--accent-red)',
  };

  return (
    <nav className="navbar" id="main-navbar">
      <div className="navbar-left">
        <div className="navbar-logo">
          <span className="logo-icon">🏟️</span>
          <div className="navbar-title-group">
            <h1 className="navbar-title">CrowdPulse</h1>
            <span className="navbar-subtitle">{STADIUM.name}</span>
          </div>
        </div>
      </div>

      <div className="navbar-center">
        <div className="live-badge">
          <span className="live-dot" />
          <span className="live-text">LIVE</span>
        </div>
        <span className="match-label">IPL 2026 — Match Day</span>
      </div>

      <div className="navbar-right">
        <div className="navbar-time font-mono">
          {time.toLocaleTimeString('en-IN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          })}
        </div>
        <div className="connection-indicator">
          <span
            className="status-dot"
            style={{ background: statusColors[connectionStatus] }}
          />
          <span className="connection-label">
            {connectionStatus === 'connected' ? 'Online' : connectionStatus}
          </span>
        </div>
      </div>
    </nav>
  );
}
