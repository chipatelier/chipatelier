import axios from "axios";

/**
 * Shared Axios instance for all ChipAtelier API calls.
 * withCredentials=true ensures httpOnly cookies (refresh token) are sent automatically.
 */
export const apiClient = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});
