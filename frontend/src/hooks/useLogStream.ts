/**
 * WebSocket hook for real-time ORFS log streaming.
 *
 * Connects to the backend WS endpoint, passing the JWT access token as a query param
 * (browsers cannot set custom headers for WebSocket connections).
 *
 * Behavior:
 *   - On open: connection established, calls onLine for each received line
 *   - On message: calls onLine(event.data) for each text frame
 *   - On close (job still running): reconnects after 2s backoff
 *   - On unmount: closes WebSocket cleanly
 *
 * Returns: { connected: boolean }
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useStore } from "../store";
import { refresh } from "../api/auth";

const RECONNECT_DELAY_MS = 2000;

/** Decode JWT exp field client-side (no verification — just to check expiry). */
function isTokenExpiredOrExpiring(token: string, bufferSecs = 60): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    if (typeof payload.exp !== "number") return true;
    return Date.now() / 1000 > payload.exp - bufferSecs;
  } catch {
    return true;
  }
}

interface UseLogStreamOptions {
  /** If true, attempt reconnect on unexpected close (for running jobs). */
  reconnect?: boolean;
}

export function useLogStream(
  runId: string | null,
  onLine: (line: string) => void,
  options: UseLogStreamOptions = {}
): { connected: boolean } {
  const { reconnect = true } = options;
  const accessToken = useStore((s) => s.accessToken);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);

  // Stable callback ref — avoids stale closures in WS event handlers
  const onLineRef = useRef(onLine);
  onLineRef.current = onLine;

  const connect = useCallback(async () => {
    if (!runId || !accessToken || unmountedRef.current) return;

    // Refresh the token proactively if expired or expiring soon.
    // WebSocket connections bypass Axios, so the HTTP 401-refresh interceptor
    // never fires — we must handle it here before opening the socket.
    let token = accessToken;
    if (isTokenExpiredOrExpiring(token)) {
      try {
        const tokenResponse = await refresh();
        token = tokenResponse.access_token;
        useStore.getState().setAccessToken(token);
      } catch {
        // Refresh token is also invalid — force re-login
        useStore.getState().clearAuth();
        window.location.href = "/login";
        return;
      }
    }

    if (unmountedRef.current) return;

    // Determine WS URL: use wss:// in production, ws:// in dev
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const host = window.location.host;
    const url = `${proto}://${host}/api/v1/ws/jobs/${runId}/logs/stream?token=${encodeURIComponent(token)}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!unmountedRef.current) setConnected(true);
    };

    ws.onmessage = (event: MessageEvent) => {
      if (typeof event.data === "string") {
        onLineRef.current(event.data);
      }
    };

    ws.onclose = () => {
      if (unmountedRef.current) return;
      setConnected(false);
      if (reconnect) {
        reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS);
      }
    };

    ws.onerror = () => {
      // onclose will fire after onerror — reconnect handled there
    };
  }, [runId, accessToken, reconnect]);

  useEffect(() => {
    unmountedRef.current = false;
    connect();

    return () => {
      unmountedRef.current = true;
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setConnected(false);
    };
  }, [connect]);

  return { connected };
}
