/**
 * CrowdsourcedFeed — Real-time chat/report feed.
 *
 * Bidirectional: spectators submit reports, security broadcasts alerts.
 * Message types: REPORT, ALERT, BROADCAST.
 * Auto-scrolls with new message indicators.
 */

import { useState, useRef, useEffect } from 'react';

const MESSAGE_TYPES = {
  REPORT: { icon: '📝', color: 'var(--accent-blue)', label: 'Report' },
  ALERT: { icon: '⚠️', color: 'var(--accent-amber)', label: 'Alert' },
  BROADCAST: { icon: '📢', color: 'var(--accent-purple)', label: 'Broadcast' },
};

// Demo messages for prototype — in production, wired to Firestore
const DEMO_MESSAGES = [
  {
    id: '1',
    type: 'BROADCAST',
    sender: 'Security HQ',
    text: 'Gates open in 15 minutes. All units confirm readiness.',
    timestamp: new Date(Date.now() - 600_000).toISOString(),
  },
  {
    id: '2',
    type: 'REPORT',
    sender: 'Sector B Volunteer',
    text: 'Large crowd forming near Gate B food court. Requesting additional marshals.',
    timestamp: new Date(Date.now() - 420_000).toISOString(),
  },
  {
    id: '3',
    type: 'ALERT',
    sender: 'AI Agent',
    text: 'Gate D density approaching WARNING threshold (1.4 ped/m²). Reroute recommended.',
    timestamp: new Date(Date.now() - 180_000).toISOString(),
  },
  {
    id: '4',
    type: 'REPORT',
    sender: 'Mobile Team 3',
    text: 'Medical station near Gate F fully operational. 2 EMTs on standby.',
    timestamp: new Date(Date.now() - 60_000).toISOString(),
  },
  {
    id: '5',
    type: 'BROADCAST',
    sender: 'Orchestrator Agent',
    text: 'Dynamic signage updated: Gate A → "Fast Entry", Gate D → "Use Gate E"',
    timestamp: new Date(Date.now() - 30_000).toISOString(),
  },
];

export default function CrowdsourcedFeed({ messages: externalMessages, onSubmitReport }) {
  const [localMessages, setLocalMessages] = useState(DEMO_MESSAGES);
  const [input, setInput] = useState('');
  const feedRef = useRef(null);
  const messages = externalMessages || localMessages;

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    if (onSubmitReport) {
      onSubmitReport({
        type: 'REPORT',
        sender: 'You',
        text: input.trim(),
        timestamp: new Date().toISOString(),
      });
    } else {
      const newMsg = {
        id: Date.now().toString(),
        type: 'REPORT',
        sender: 'You',
        text: input.trim(),
        timestamp: new Date().toISOString(),
      };
      setLocalMessages((prev) => [...prev, newMsg]);
    }
    setInput('');
  };

  const formatTime = (iso) => {
    const d = new Date(iso);
    return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="crowdsourced-feed" id="crowdsourced-feed">
      <div className="feed-header">
        <h3>
          <span>💬</span> Field Reports
        </h3>
        <span className="feed-count font-mono">{messages.length} messages</span>
      </div>

      <div className="feed-messages" ref={feedRef}>
        {messages.map((msg) => {
          const typeInfo = MESSAGE_TYPES[msg.type] || MESSAGE_TYPES.REPORT;
          return (
            <div
              className={`feed-message feed-message-${msg.type.toLowerCase()}`}
              key={msg.id}
            >
              <div className="message-header">
                <span className="message-type-icon">{typeInfo.icon}</span>
                <span className="message-sender" style={{ color: typeInfo.color }}>
                  {msg.sender}
                </span>
                <span className="message-time font-mono">{formatTime(msg.timestamp)}</span>
              </div>
              <p className="message-text">{msg.text}</p>
            </div>
          );
        })}
      </div>

      <form className="feed-input-form" onSubmit={handleSubmit}>
        <input
          className="input-dark"
          type="text"
          placeholder="Submit a field report…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          id="feed-input"
        />
        <button className="btn-primary" type="submit" id="feed-submit">
          Send
        </button>
      </form>
    </div>
  );
}
