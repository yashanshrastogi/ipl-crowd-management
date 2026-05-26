import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import useWebSocket from './useWebSocket';

class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  static instances = [];

  constructor(url) {
    this.url = url;
    this.readyState = MockWebSocket.CONNECTING;
    this.sent = [];
    this.onopen = null;
    this.onmessage = null;
    this.onclose = null;
    this.onerror = null;
    MockWebSocket.instances.push(this);
  }

  send(message) {
    this.sent.push(message);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  }

  open() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.();
  }

  receive(data) {
    this.onmessage?.({ data });
  }
}

describe('useWebSocket', () => {
  const originalWebSocket = globalThis.WebSocket;

  beforeEach(() => {
    vi.useFakeTimers();
    MockWebSocket.instances = [];
    globalThis.WebSocket = MockWebSocket;
  });

  afterEach(() => {
    vi.useRealTimers();
    globalThis.WebSocket = originalWebSocket;
  });

  it('connects, parses messages, and sends JSON payloads', () => {
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost/ws', { reconnectDelay: 100 }),
    );

    act(() => {
      vi.runOnlyPendingTimers();
    });

    const socket = MockWebSocket.instances[0];
    act(() => {
      socket.open();
      socket.receive('{"density":2.1}');
    });

    expect(result.current.readyState).toBe(MockWebSocket.OPEN);
    expect(result.current.lastMessage).toEqual({ density: 2.1 });

    act(() => {
      result.current.sendMessage({ command: 'ping' });
    });

    expect(socket.sent).toEqual(['{"command":"ping"}']);
  });

  it('does not reconnect after an intentional disconnect', () => {
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost/ws', { reconnectDelay: 100 }),
    );

    act(() => {
      vi.runOnlyPendingTimers();
    });

    expect(MockWebSocket.instances).toHaveLength(1);

    act(() => {
      result.current.disconnect();
      vi.advanceTimersByTime(1_000);
    });

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(result.current.readyState).toBe(MockWebSocket.CLOSED);
  });
});
