/**
 * Typed API client for project and run endpoints.
 * All functions use the shared apiClient (axios instance with credentials).
 */
import { apiClient } from "./client";

// ---------------------------------------------------------------------------
// Response types (matching backend Pydantic schemas)
// ---------------------------------------------------------------------------

export interface ProjectResponse {
  id: string;
  name: string;
  pdk: string;
  storage_bytes: number;
  created_at: string;
  run_count: number;
}

export interface RunSummary {
  id: string;
  status: string;
  target_stage: string | null;
  stage_completed: string | null;
  created_at: string;
  completed_at: string | null;
  ppa: Record<string, number | string> | null;
}

export interface UploadResponse {
  source_path: string;
  file_count: number;
}

// ---------------------------------------------------------------------------
// Project endpoints
// ---------------------------------------------------------------------------

/**
 * List all projects for the authenticated user.
 */
export async function listProjects(): Promise<ProjectResponse[]> {
  const { data } = await apiClient.get<ProjectResponse[]>("/projects");
  return data;
}

/**
 * Create a new project.
 */
export async function createProject(params: {
  name: string;
  pdk?: string;
}): Promise<ProjectResponse> {
  const { data } = await apiClient.post<ProjectResponse>("/projects", params);
  return data;
}

/**
 * Get a single project by ID.
 */
export async function getProject(id: string): Promise<ProjectResponse> {
  const { data } = await apiClient.get<ProjectResponse>(`/projects/${id}`);
  return data;
}

/**
 * List all runs for a project.
 */
export async function listRuns(projectId: string): Promise<RunSummary[]> {
  const { data } = await apiClient.get<RunSummary[]>(`/projects/${projectId}/runs`);
  return data;
}

/**
 * Upload Verilog/config files for a project.
 */
export async function uploadFiles(
  projectId: string,
  files: File[],
  topModule?: string
): Promise<UploadResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  if (topModule) {
    formData.append("top_module", topModule);
  }
  const { data } = await apiClient.post<UploadResponse>(
    `/projects/${projectId}/upload`,
    formData,
    // Do NOT set Content-Type manually — Axios auto-sets multipart/form-data
    // with the correct boundary when it detects a FormData body. Explicitly
    // setting it without a boundary causes the server to return 422.
    { headers: { "Content-Type": undefined } }
  );
  return data;
}
