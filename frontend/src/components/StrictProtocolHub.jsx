/**
 * StrictProtocolHub — Emergency-style red-alert panel.
 *
 * Displays banned items, flashing pulse animation,
 * and dynamic updates from Firestore strict_protocol flags.
 */

import { BANNED_ITEMS } from '../utils/constants';

export default function StrictProtocolHub({ active = false, activatedGates = [] }) {
  if (!active) {
    return (
      <div className="strict-protocol-hub" id="strict-protocol-hub">
        <div className="protocol-header">
          <span className="protocol-icon">🛡️</span>
          <h3>Security Protocol</h3>
        </div>
        <div className="protocol-status-normal">
          <span className="status-dot status-clear" />
          <span>Standard screening — all gates nominal</span>
        </div>
        <div className="banned-items-grid">
          {BANNED_ITEMS.map((item) => (
            <div className="banned-item" key={item.label}>
              <span className="banned-icon">{item.icon}</span>
              <span className="banned-label">{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="strict-protocol-hub alert-danger" id="strict-protocol-hub">
      <div className="protocol-header protocol-header-active">
        <span className="protocol-alert-icon">🚨</span>
        <div>
          <h3 className="protocol-title-active">STRICT PROTOCOL</h3>
          <p className="protocol-subtitle-active">
            Enhanced screening at {activatedGates.length || 'all'} gate
            {activatedGates.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      <div className="protocol-active-gates">
        {activatedGates.length > 0 ? (
          activatedGates.map((gateId) => (
            <span key={gateId} className="badge badge-red">
              {gateId.replace('gate_', 'Gate ').toUpperCase()}
            </span>
          ))
        ) : (
          <span className="badge badge-red">ALL GATES</span>
        )}
      </div>

      <div className="banned-items-grid banned-items-active">
        {BANNED_ITEMS.map((item) => (
          <div className="banned-item banned-item-active" key={item.label}>
            <span className="banned-icon">{item.icon}</span>
            <div>
              <span className="banned-label">{item.label}</span>
              <span className="banned-detail">{item.detail}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="protocol-instructions">
        <p>📢 Prepare credentials • Remove all prohibited items • Follow staff directions</p>
      </div>
    </div>
  );
}
