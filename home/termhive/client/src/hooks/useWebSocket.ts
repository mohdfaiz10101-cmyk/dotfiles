import { useEffect, useRef, useCallback, useState } from 'react';

export type WSMessage = {
  type: string;
  agentId?: string;
  data?: string;
  status?: string;
  projectId?: string;
  filename?: string;
};

export const WS_MESSAGE_EVENT = 'termhive:ws-message';
export const WS_OPEN_EVENT = 'termhive:ws-open';

type MessageHandler = (msg: WSMessage) => void;
export type WebSocketState = 'connecting' | 'connected' | 'reconnecting';

export function useWebSocket(onMessage: MessageHandler) {
  const wsRef = useRef<WebSocket | null>(null);
  const queueRef = useRef<object[]>([]);
  const [state, setState] = useState<WebSocketState>('connecting');
  const handlersRef = useRef(onMessage);
  handlersRef.current = onMessage;

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws`;
    let disposed = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let attempts = 0;
    let openedOnce = false;

    const connect = () => {
      if (disposed) return;
      setState(attempts === 0 ? 'connecting' : 'reconnecting');
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        attempts = 0;
        setState('connected');

        const queued = queueRef.current.splice(0);
        for (let i = 0; i < queued.length; i += 1) {
          if (ws.readyState !== WebSocket.OPEN) {
            queueRef.current.unshift(...queued.slice(i));
            break;
          }
          ws.send(JSON.stringify(queued[i]));
        }
        // Initial mounts already queued their attach messages. Only mounted
        // consumers need an explicit re-attach after a later reconnect.
        if (openedOnce) window.dispatchEvent(new CustomEvent(WS_OPEN_EVENT));
        openedOnce = true;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WSMessage;
          handlersRef.current(msg);
          window.dispatchEvent(new CustomEvent(WS_MESSAGE_EVENT, { detail: msg }));
        } catch { /* ignore malformed frames */ }
      };

      ws.onerror = () => {
        // onclose schedules the retry; close explicitly for browsers that
        // otherwise leave a failed CONNECTING socket hanging.
        try { ws.close(); } catch { /* ignore */ }
      };

      ws.onclose = () => {
        if (wsRef.current === ws) {
          wsRef.current = null;
        }
        if (disposed) return;
        setState('reconnecting');
        const delay = Math.min(10_000, 500 * (2 ** attempts));
        attempts += 1;
        retryTimer = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      disposed = true;
      if (retryTimer) clearTimeout(retryTimer);
      const ws = wsRef.current;
      wsRef.current = null;
      try { ws?.close(); } catch { /* ignore */ }
    };
  }, []);

  const send = useCallback((msg: object) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    } else {
      // Keep commands issued during a brief mobile network transition. Bound
      // the queue so a long offline period cannot grow memory indefinitely.
      if (queueRef.current.length >= 500) queueRef.current.shift();
      queueRef.current.push(msg);
    }
  }, []);

  return { send, wsRef, state };
}
