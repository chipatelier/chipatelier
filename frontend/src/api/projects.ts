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
  config_version: number;
  verilog_version: number;
  latest_source_path: string | null;
}

export interface ProjectSourceResponse {
  filename: string;
  content: string;
  version: number;
}

export interface ProjectConfigResponse {
  content: string;
  version: number;
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
  );
  return data;
}

/**
 * Delete a project by ID.
 */
export async function deleteProject(id: string): Promise<void> {
  await apiClient.delete(`/projects/${id}`);
}

/**
 * Update a project (name and/or config).
 */
export async function updateProject(
  id: string,
  body: { name?: string; config_mk?: string }
): Promise<ProjectResponse> {
  const { data } = await apiClient.patch<ProjectResponse>(`/projects/${id}`, body);
  return data;
}

/**
 * Get project source files.
 */
export async function getProjectSource(id: string): Promise<ProjectSourceResponse> {
  const { data } = await apiClient.get<ProjectSourceResponse>(`/projects/${id}/source`);
  return data;
}

/**
 * Get project config.
 */
export async function getProjectConfig(id: string): Promise<ProjectConfigResponse> {
  const { data } = await apiClient.get<ProjectConfigResponse>(`/projects/${id}/config`);
  return data;
}
