import { apiClient } from "../api/client";
import { refresh } from "../api/auth";
import { useStore } from "../store";

type FailedRequest = {
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
};

let isRefreshing = false;
let failedQueue: FailedRequest[] = [];

function processQueue(error: unknown, token: string | null): void {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else if (token) {
      resolve(token);
    }
  });
  failedQueue = [];
}

/**
 * Setup Axios interceptors for transparent JWT refresh on 401 responses.
 *
 * - Attaches the current access token as Authorization: Bearer on every request.
 * - On 401 (except for /auth/refresh itself), attempts to refresh the token.
 * - Queues concurrent failing requests and retries them once the token is renewed.
 * - If refresh fails, clears auth state and redirects to /login.
 *
 * Call this once in App.tsx via useEffect on mount.
 */
export function setupTokenRefreshInterceptor(): void {
  // Request interceptor: attach current access token
  apiClient.interceptors.request.use(
    (config) => {
      const token = useStore.getState().accessToken;
      if (token && config.headers) {
        config.headers["Authorization"] = `Bearer ${token}`;
      }
      return config;
    },
    (error) => Promise.reject(error)
  );

  // Response interceptor: handle 401 by refreshing token
  apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config;

      // Skip refresh loop for the refresh endpoint itself
      if (originalRequest?.url?.includes("/auth/refresh")) {
        return Promise.reject(error);
      }

      if (error.response?.status === 401 && !originalRequest?._retry) {
        if (isRefreshing) {
          // Queue this request until the in-flight refresh completes
          return new Promise<string>((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          })
            .then((token) => {
              originalRequest.headers["Authorization"] = `Bearer ${token}`;
              return apiClient(originalRequest);
            })
            .catch((err) => Promise.reject(err));
        }

        originalRequest._retry = true;
        isRefreshing = true;

        try {
          const tokenResponse = await refresh();
          const newToken = tokenResponse.access_token;
          useStore.getState().setAccessToken(newToken);
          processQueue(null, newToken);
          originalRequest.headers["Authorization"] = `Bearer ${newToken}`;
          return apiClient(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);
          useStore.getState().clearAuth();
          window.location.href = "/login";
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      }

      return Promise.reject(error);
    }
  );
}
