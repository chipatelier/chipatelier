/**
 * WebSocket hook for grade result streaming.
 *
 * Connects to the grade stream endpoint and waits for a single JSON message
 * containing the evaluation result. Closes the connection after receipt.
 *
 * If the connection drops before a grade is received, retries with exponential
 * backoff (up to WS_MAX_RECONNECT_ATTEMPTS).
 *
 * WS URL: /api/v1/ws/runs/{runId}/grade/stream?token={accessToken}
 *
 * Returns: { gradeResult: GradeResult | null, isConnected: boolean }
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useStore } from "../store";
import { refresh } from "../api/auth";
import { GradeResult } from "../store/courseSlice";
import {
  WS_RECONNECT_BASE_MS,
  WS_RECONNECT_MAX_MS,
  WS_MAX_RECONNECT_ATTEMPTS,
  TOKEN_EXPIRY_BUFFER_SECS,
} from "../constants";

/** Decode JWT exp field client-side (no verification — just to check expiry). */
function isTokenExpiredOrExpiring(token: string, bufferSecs = TOKEN_EXPIRY_BUFFER_SECS): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    if (typeof payload.exp !== "number") return true;
    return Date.now() / 1000 > payload.exp - bufferSecs;
  } catch {
    return true;
  }
}

export function useGradeStream(runId: string | null): {
  gradeResult: GradeResult | null;
  isConnected: boolean;
} {
  const accessToken = useStore((s) => s.accessToken);
  const setGradeResult = useStore((s) => s.setGradeResult);
  const [gradeResult, setLocalGradeResult] = useState<GradeResult | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);
  const attemptRef = useRef(0);
  const receivedRef = useRef(false);

  const connect = useCallback(async () => {
    if (!runId || !accessToken || unmountedRef.current) return;

    // Refresh token proactively if expired — WebSocket bypasses Axios interceptors
    let token = accessToken;
    if (isTokenExpiredOrExpiring(token)) {
      try {
        const tokenResponse = await refresh();
        token = tokenResponse.access_token;
        useStore.getState().setAccessToken(token);
      } catch {
        useStore.getState().clearAuth();
        window.location.href = "/login";
        return;
      }
    }

    if (unmountedRef.current) return;

    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const host = window.location.host;
    const url = `${proto}://${host}/api/v1/ws/runs/${runId}/grade/stream?token=${encodeURIComponent(token)}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!unmountedRef.current) {
        setIsConnected(true);
        attemptRef.current = 0;
      }
    };

    ws.onmessage = (event: MessageEvent) => {
      if (typeof event.data === "string") {
        try {
          const result = JSON.parse(event.data) as GradeResult;
          if (!unmountedRef.current) {
            receivedRef.current = true;
            setLocalGradeResult(result);
            setGradeResult(runId, result);
          }
        } catch {
          // Malformed JSON from server — ignore
        }
        // Close after receiving the single grade message
        ws.close();
      }
    };

    ws.onclose = () => {
      if (unmountedRef.current) return;
      setIsConnected(false);
      // Retry if we haven't received the grade yet
      if (!receivedRef.current && attemptRef.current < WS_MAX_RECONNECT_ATTEMPTS) {
        const delay = Math.min(
          WS_RECONNECT_BASE_MS * Math.pow(2, attemptRef.current),
          WS_RECONNECT_MAX_MS
        );
        attemptRef.current += 1;
        reconnectTimer.current = setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      // onclose will fire after onerror
    };
  }, [runId, accessToken, setGradeResult]);

  useEffect(() => {
    unmountedRef.current = false;
    receivedRef.current = false;
    attemptRef.current = 0;
    setLocalGradeResult(null);
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
      setIsConnected(false);
    };
  }, [connect]);

  return { gradeResult, isConnected };
}
