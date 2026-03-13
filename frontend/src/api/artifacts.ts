/**
 * Typed API client for artifact download endpoints.
 * Returns presigned MinIO URLs for GDS, DEF, timing reports, and layout PNG.
 */
import { apiClient } from "./client";

// ---------------------------------------------------------------------------
// Response types (matching backend ArtifactURLs schema)
// ---------------------------------------------------------------------------

export interface ArtifactURLs {
  gds_url: string | null;
  def_url: string | null;
  timing_report_url: string | null;
  layout_png_url: string | null;
  run_id: string;
  expires_in_seconds: number;
}

// ---------------------------------------------------------------------------
// Artifact endpoints
// ---------------------------------------------------------------------------

/**
 * Get presigned download URLs for a completed run's artifacts.
 * Returns 404 if artifacts are not yet available (job still running or failed).
 */
export async function getArtifacts(runId: string): Promise<ArtifactURLs> {
  const { data } = await apiClient.get<ArtifactURLs>(`/jobs/${runId}/artifacts`);
  return data;
}
