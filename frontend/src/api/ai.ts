/**
 * Typed API client for AI endpoints (explain + advisor + chat streaming).
 * Uses the shared apiClient (axios instance with credentials) from api/client.ts.
 * Chat streaming uses the native fetch API with ReadableStream for NDJSON.
 *
 * Privacy constraint (CLAUDE.md):
 *   These calls contain only run_id — the server-side context_builder assembles
 *   log_tail, ppa, and config. GDS/DEF contents never leave the server.
 */
import { apiClient } from "./client";

// ---------------------------------------------------------------------------
// Response types (matching backend Pydantic schemas)
// ---------------------------------------------------------------------------

export interface ExplainResponse {
  explanation: string;
  model: string;
}

export interface AdvisorResponse {
  suggestions: string;
  model: string;
}

// ---------------------------------------------------------------------------
// Explain endpoints
// ---------------------------------------------------------------------------

/**
 * Explain ORFS log errors in plain language.
 */
export async function explainLog(
  runId: string,
  logLines?: number
): Promise<ExplainResponse> {
  const { data } = await apiClient.post<ExplainResponse>("/ai/explain/log", {
    run_id: runId,
    log_lines: logLines ?? 100,
  });
  return data;
}

/**
 * Explain timing violations (WNS/TNS) for a run.
 */
export async function explainTiming(runId: string): Promise<ExplainResponse> {
  const { data } = await apiClient.post<ExplainResponse>("/ai/explain/timing", {
    run_id: runId,
    log_lines: 100,
  });
  return data;
}

/**
 * Explain DRC routing violations for a run.
 */
export async function explainDrc(runId: string): Promise<ExplainResponse> {
  const { data } = await apiClient.post<ExplainResponse>("/ai/explain/drc", {
    run_id: runId,
    log_lines: 100,
  });
  return data;
}

// ---------------------------------------------------------------------------
// Advisor endpoint
// ---------------------------------------------------------------------------

/**
 * Get config parameter suggestions grounded in run PPA metrics.
 */
export async function advisorConfig(runId: string): Promise<AdvisorResponse> {
  const { data } = await apiClient.post<AdvisorResponse>("/ai/advisor/config", {
    run_id: runId,
  });
  return data;
}

// ---------------------------------------------------------------------------
// Chat streaming
// ---------------------------------------------------------------------------

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

/**
 * Stream a multi-turn chat response from the backend as an async generator.
 *
 * Yields parsed NDJSON chunks: { token?: string } | { done?: boolean } | { error?: string }
 * Uses native fetch + ReadableStream to avoid axios buffering the streaming response.
 *
 * Privacy constraint: only run_id and message history are sent — design files never leave server.
 */
export async function* streamChat(
  runId: string,
  message: string,
  history: ChatMessage[],
  accessToken: string,
): AsyncGenerator<{ token?: string; done?: boolean; error?: string }> {
  const resp = await fetch("/api/v1/ai/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ run_id: runId, message, history }),
  });

  if (!resp.ok || !resp.body) {
    if (resp.status === 503) {
      yield { error: "AI assistant is currently unavailable. Contact your instructor if this persists." };
      return;
    }
    throw new Error(`Chat request failed: ${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) continue;
      yield JSON.parse(line);
    }
  }

  // Process any remaining buffer
  if (buf.trim()) {
    yield JSON.parse(buf);
  }
}
