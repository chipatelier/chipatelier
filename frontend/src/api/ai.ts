/**
 * Typed API client for AI endpoints (explain + advisor).
 * Uses the shared apiClient (axios instance with credentials) from api/client.ts.
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
