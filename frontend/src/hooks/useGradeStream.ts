/**
 * WebSocket hook for grade result streaming.
 *
 * Connects to the grade stream endpoint and waits for a single JSON message
 * containing the evaluation result. Closes the connection after receipt.
 *
 * Mirrors the useLogStream.ts pattern — same token refresh, same WS lifecycle.
 *
 * WS URL: /api/v1/ws/runs/{runId}/grade/stream?token={accessToken}
 *
 * Returns: { gradeResult: GradeResult | null, isConnected: boolean }
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useStore } from "../store";
import { refresh } from "../api/auth";
import { GradeResult } from "../store/courseSlice";

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

export function useGradeStream(runId: string | null): {
  gradeResult: GradeResult | null;
  isConnected: boolean;
} {
  const accessToken = useStore((s) => s.accessToken);
  const setGradeResult = useStore((s) => s.setGradeResult);
  const [gradeResult, setLocalGradeResult] = useState<GradeResult | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const unmountedRef = useRef(false);

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
      if (!unmountedRef.current) setIsConnected(true);
    };

    ws.onmessage = (event: MessageEvent) => {
      if (typeof event.data === "string") {
        try {
          const result = JSON.parse(event.data) as GradeResult;
          if (!unmountedRef.current) {
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
      if (!unmountedRef.current) {
        setIsConnected(false);
      }
    };

    ws.onerror = () => {
      // onclose will fire after onerror
    };
  }, [runId, accessToken, setGradeResult]);

  useEffect(() => {
    unmountedRef.current = false;
    setLocalGradeResult(null);
    connect();

    return () => {
      unmountedRef.current = true;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setIsConnected(false);
    };
  }, [connect]);

  return { gradeResult, isConnected };
}
