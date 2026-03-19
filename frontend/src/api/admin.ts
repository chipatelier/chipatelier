import { apiClient } from "./client";

/**
 * Generate a one-time password reset token for a user (admin only).
 * Returns the token and its TTL in seconds.
 */
export async function generateResetToken(
  email: string
): Promise<{ token: string; expires_in_seconds: number }> {
  const { data } = await apiClient.post<{ token: string; expires_in_seconds: number }>(
    "/admin/reset-token",
    { email }
  );
  return data;
}
