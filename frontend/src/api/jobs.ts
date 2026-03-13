/**
 * Typed API client for job endpoints.
 * All functions use the shared apiClient (axios instance with credentials).
 */
import { apiClient } from "./client";

// ---------------------------------------------------------------------------
// Request / Response types (matching backend Pydantic schemas)
// ---------------------------------------------------------------------------

export interface SubmitRequest {
  project_id: string;
  target_stage?: string;
  config_overrides?: Record<string, unknown>;
  source_path?: string;  // Path to uploaded files in MinIO
}

export interface SubmitResponse {
  run_id: string;
  status: string;
}

export interface RunStatusResponse {
  id: string;
  status: string;
  stage_completed: string | null;
  target_stage: string | null;
  created_at: string;
  completed_at: string | null;
  ppa: Record<string, number | string | boolean | null> | null;
  config: Record<string, unknown> | null;
}

export interface LogHistoryResponse {
  lines: string[];
  total: number;
}

// ---------------------------------------------------------------------------
// Job endpoints
// ---------------------------------------------------------------------------

/**
 * Submit a new ORFS flow job.
 */
export async function submitJob(data: SubmitRequest): Promise<SubmitResponse> {
  const { data: resp } = await apiClient.post<SubmitResponse>("/jobs/submit", data);
  return resp;
}

/**
 * Get current status and metrics for a run.
 */
export async function getJobStatus(runId: string): Promise<RunStatusResponse> {
  const { data } = await apiClient.get<RunStatusResponse>(`/jobs/${runId}`);
  return data;
}

/**
 * Cancel a queued or running job.
 */
export async function cancelJob(runId: string): Promise<void> {
  await apiClient.delete(`/jobs/${runId}`);
}

/**
 * Get full log history for a run (REST fallback for completed runs).
 * Returns lines from Redis logbuf (24hr TTL).
 */
export async function getLogHistory(runId: string): Promise<LogHistoryResponse> {
  const { data } = await apiClient.get<LogHistoryResponse>(`/jobs/${runId}/logs`);
  return data;
}
