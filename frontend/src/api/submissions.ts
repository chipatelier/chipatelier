/**
 * Typed API client for submission endpoints.
 * All functions use the shared apiClient (axios instance with credentials).
 */
import { apiClient } from "./client";

// ---------------------------------------------------------------------------
// Types matching backend Pydantic schemas
// ---------------------------------------------------------------------------

export interface CheckpointHardResult {
  metric: string;
  op: string;
  threshold: number | boolean;
  actual: number | boolean | null;
  passed: boolean;
}

export interface CheckpointScoredResult {
  metric: string;
  op: string;
  threshold: number;
  actual: number | null;
  passed: boolean;
  awarded: number;
  max_points: number;
  partial_credit: boolean;
}

export interface CheckpointResults {
  hard: CheckpointHardResult[];
  scored: CheckpointScoredResult[];
  hard_gate_blocked: boolean;
}

export interface SubmissionResponse {
  id: string;
  assignment_id: string;
  run_id: string;
  user_id: string;
  score: number | null;
  grading_status: string;
  checkpoint_results: CheckpointResults | null;
  submitted_at: string;
}

export interface PreviewScoreResponse {
  checkpoint_results: CheckpointResults;
  score: number;
  is_eligible: boolean;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/**
 * Submit a completed run for grading.
 * Returns 422 if locked params mismatch or 400 if run is not complete.
 */
export async function submitRun(
  assignmentId: string,
  runId: string
): Promise<SubmissionResponse> {
  const { data } = await apiClient.post<SubmissionResponse>(
    `/assignments/${assignmentId}/submit`,
    { run_id: runId }
  );
  return data;
}

/**
 * List all of the current user's submissions for an assignment.
 * Ordered by submitted_at descending (most recent first).
 */
export async function getMySubmissions(
  assignmentId: string
): Promise<SubmissionResponse[]> {
  const { data } = await apiClient.get<SubmissionResponse[]>(
    `/assignments/${assignmentId}/submissions/mine`
  );
  return data;
}

/**
 * Preview checkpoint score for a run without creating a submission.
 * Uses server-side evaluation for consistency with the grading task.
 */
export async function getPreviewScore(
  assignmentId: string,
  runId: string
): Promise<PreviewScoreResponse> {
  const { data } = await apiClient.get<PreviewScoreResponse>(
    `/assignments/${assignmentId}/preview-score`,
    { params: { run_id: runId } }
  );
  return data;
}
