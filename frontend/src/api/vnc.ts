/**
 * VNC session API client.
 *
 * Provides typed functions for VNC session lifecycle:
 *   - startVncSession(runId)  → VncStartResponse (session_id, token, vnc_url)
 *   - stopVncSession(sessionId)
 *
 * The caller opens vnc_url in a new tab:
 *   window.open(response.vnc_url, "_blank")
 */
import { apiClient } from "./client";

export interface VncStartResponse {
  session_id: string;
  token: string;
  vnc_url: string; // "/vnc/{token}" — open in new tab
  expires_at: string; // ISO datetime
}

/**
 * Start a VNC session for a completed run.
 *
 * Returns a VncStartResponse containing the vnc_url to open in a new tab.
 * The vnc_url embeds the HMAC-signed token in the URL path (not query string).
 *
 * @throws 400 if run is not complete or has no artifacts.
 * @throws 429 if MAX_VNC_SESSIONS limit is reached.
 */
export async function startVncSession(runId: string): Promise<VncStartResponse> {
  const resp = await apiClient.post<VncStartResponse>(`/api/v1/vnc/start/${runId}`);
  return resp.data;
}

/**
 * Stop an active VNC session and its container.
 *
 * @throws 404 if session not found.
 * @throws 403 if session does not belong to the current user.
 */
export async function stopVncSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/api/v1/vnc/${sessionId}`);
}
