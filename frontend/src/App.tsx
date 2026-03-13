import React, { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { setupTokenRefreshInterceptor } from "./hooks/useTokenRefresh";
import { useStore } from "./store";
import { getMe, refresh } from "./api/auth";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import ProjectListPage from "./pages/ProjectListPage";
import ProjectPage from "./pages/ProjectPage";
import RunDetailPage from "./pages/RunDetailPage";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

function ProtectedRoute({ children }: ProtectedRouteProps): React.ReactElement {
  const accessToken = useStore((s) => s.accessToken);
  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export default function App(): React.ReactElement {
  const [sessionLoading, setSessionLoading] = useState(true);
  const setAuth = useStore((s) => s.setAuth);
  const accessToken = useStore((s) => s.accessToken);

  // Setup token refresh interceptor once on mount
  useEffect(() => {
    setupTokenRefreshInterceptor();
  }, []);

  // Restore session on page refresh:
  // If we already have an access token, try getMe; otherwise try refresh → getMe.
  useEffect(() => {
    async function restoreSession(): Promise<void> {
      try {
        if (accessToken) {
          const user = await getMe();
          setAuth(user, accessToken);
        } else {
          const tokenResp = await refresh();
          const user = await getMe();
          setAuth(user, tokenResp.access_token);
        }
      } catch {
        // No valid session — user will see login page
      } finally {
        setSessionLoading(false);
      }
    }

    restoreSession();
    // Only run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (sessionLoading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "sans-serif",
          color: "#666",
          background: "#0d1117",
        }}
      >
        Loading...
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Protected routes */}
        <Route
          path="/projects"
          element={
            <ProtectedRoute>
              <ProjectListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects/:id"
          element={
            <ProtectedRoute>
              <ProjectPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects/:id/runs/:runId"
          element={
            <ProtectedRoute>
              <RunDetailPage />
            </ProtectedRoute>
          }
        />

        {/* Root redirect */}
        <Route path="/" element={<Navigate to="/projects" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
