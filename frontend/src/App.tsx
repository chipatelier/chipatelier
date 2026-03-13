import React, { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { setupTokenRefreshInterceptor } from "./hooks/useTokenRefresh";
import { useStore } from "./store";
import { getMe, refresh, logout as authLogout } from "./api/auth";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

// Placeholder until plan 01-03 implements the full project list UI
function ProjectListPage(): React.ReactElement {
  const user = useStore((s) => s.user);
  const clearAuth = useStore((s) => s.clearAuth);
  const storageMB = user ? (user.storage_used_bytes / 1024 / 1024).toFixed(1) : "0";

  function handleLogout(): void {
    authLogout()
      .catch(() => undefined)
      .finally(() => {
        clearAuth();
        window.location.href = "/login";
      });
  }

  return (
    <div style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>ChipAtelier</h1>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          {user && (
            <span style={{ fontSize: "0.875rem", color: "#666" }}>
              {user.display_name ?? user.email} — {storageMB} MB used
            </span>
          )}
          <button onClick={handleLogout} style={{ cursor: "pointer" }}>
            Sign out
          </button>
        </div>
      </div>
      <p>Projects will appear here (implemented in plan 01-03).</p>
    </div>
  );
}

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
        }}
      >
        Loading...
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/projects"
          element={
            <ProtectedRoute>
              <ProjectListPage />
            </ProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to="/projects" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
