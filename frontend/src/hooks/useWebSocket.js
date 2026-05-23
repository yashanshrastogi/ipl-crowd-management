/**
 * useWebSocket — WebSocket connection hook for real-time updates.
 *
 * Establishes a WebSocket connection, handles reconnection with
 * exponential backoff, and provides send/close utilities.
 *
 * For the prototype we fall back to SSE / polling since the FastAPI
 * backend doesn't expose a WS endpoint yet. This hook is included
 * for future extensibility.
 */

import { useState, useEffect, useRef, useCallback } from 'react';

const DEFAULT_URL = `ws://${window.location.hostname}:8000/ws`;
const MAX_RECONNECT_DELAY = 30_000;

/**
 * @param {string} [url]  WebSocket endpoint URL
 * @param {object} [opts]
 * @param {boolean} [opts.autoConnect=true]
 * @param {number}  [opts.reconnectDelay=2000]
 * @returns {{ lastMessage, sendMessage, readyState, connect, disconnect }}
 */
export default function useWebSocket(url = DEFAULT_URL, opts = {}) {
  const { autoConnect = true, reconnectDelay = 2000 } = opts;

  const [lastMessage, setLastMessage] = useState(null);
  const [readyState, setReadyState] = useState(WebSocket.CLOSED);

  const wsRef = useRef(null);
  const retriesRef = useRef(0);
  const timerRef = useRef(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setReadyState(WebSocket.OPEN);
        retriesRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          setLastMessage(JSON.parse(event.data));
        } catch {
          setLastMessage(event.data);
        }
      };

      ws.onclose = () => {
        setReadyState(WebSocket.CLOSED);
        // Exponential backoff reconnect
        const delay = Math.min(
          reconnectDelay * 2 ** retriesRef.current,
          MAX_RECONNECT_DELAY,
        );
        retriesRef.current += 1;
        timerRef.current = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // WebSocket constructor can throw if URL is invalid
      setReadyState(WebSocket.CLOSED);
    }
  }, [url, reconnectDelay]);

  const disconnect = useCallback(() => {
    clearTimeout(timerRef.current);
    if (wsRef.current) {
      wsRef.current.onclose = null; // prevent reconnect
      wsRef.current.close();
      wsRef.current = null;
    }
    setReadyState(WebSocket.CLOSED);
  }, []);

  const sendMessage = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === 'string' ? data : JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    if (autoConnect) connect();
    return () => disconnect();
  }, [autoConnect, connect, disconnect]);

  return { lastMessage, sendMessage, readyState, connect, disconnect };
}
