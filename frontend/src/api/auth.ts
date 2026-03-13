import { apiClient } from "./client";

export interface UserResponse {
  id: string;
  email: string;
  display_name: string | null;
  role: string;
  storage_used_bytes: number;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

/**
 * Register a new user account.
 */
export async function register(
  email: string,
  password: string,
  displayName?: string
): Promise<UserResponse> {
  const { data } = await apiClient.post<UserResponse>("/auth/register", {
    email,
    password,
    display_name: displayName,
  });
  return data;
}

/**
 * Authenticate with email/password.
 * Sets httpOnly refresh cookie on the server side.
 */
export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", { email, password });
  return data;
}

/**
 * Logout — clears the refresh cookie and invalidates the jti.
 */
export async function logout(): Promise<void> {
  await apiClient.post("/auth/logout");
}

/**
 * Exchange the httpOnly refresh cookie for a new access token.
 */
export async function refresh(): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/refresh");
  return data;
}

/**
 * Fetch the current authenticated user's profile.
 */
export async function getMe(): Promise<UserResponse> {
  const { data } = await apiClient.get<UserResponse>("/users/me");
  return data;
}
