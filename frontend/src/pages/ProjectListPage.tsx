/**
 * ProjectListPage — card grid of user's projects.
 *
 * Locked design (from CONTEXT.md / PLAN must_haves):
 *   - Card per project: name, run count, created date
 *   - "New Project" button in header
 *   - Empty state for zero projects with CTA
 *   - Storage usage: "{X} GB of 5 GB used" in header
 *   - Click card → navigate to /projects/{id}
 */
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { logout as authLogout } from "../api/auth";
import { listProjects, createProject, ProjectResponse } from "../api/projects";
import { useStore } from "../store";
import { DEFAULT_QUOTA_GB } from "../constants";

export default function ProjectListPage(): React.ReactElement {
  const navigate = useNavigate();
  const user = useStore((s) => s.user);
  const clearAuth = useStore((s) => s.clearAuth);

  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewProjectForm, setShowNewProjectForm] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [creating, setCreating] = useState(false);

  const storageGB = user ? (user.storage_used_bytes / 1e9).toFixed(1) : "0.0";
  const quotaGB = user?.storage_quota_bytes
    ? (user.storage_quota_bytes / 1e9).toFixed(0)
    : String(DEFAULT_QUOTA_GB);

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch(() => setError("Failed to load projects"))
      .finally(() => setLoading(false));
  }, []);

  function handleLogout(): void {
    authLogout()
      .catch(() => undefined)
      .finally(() => {
        clearAuth();
        navigate("/login");
      });
  }

  async function handleCreateProject(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    setCreating(true);
    try {
      const proj = await createProject({ name: newProjectName.trim(), pdk: "sky130hd" });
      setProjects((prev) => [...prev, proj]);
      setNewProjectName("");
      setShowNewProjectForm(false);
    } catch {
      setError("Failed to create project");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div style={{ fontFamily: "sans-serif", minHeight: "100vh", background: "#0d1117", color: "#c9d1d9" }}>
      {/* Header */}
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "16px 24px",
          borderBottom: "1px solid #30363d",
          background: "#161b22",
        }}
      >
        <h1 style={{ margin: 0, fontSize: 20, color: "#f0f6fc" }}>ChipAtelier</h1>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          {user && (
            <span style={{ fontSize: 13, color: "#8b949e" }}>
              {storageGB} GB of {quotaGB} GB used
            </span>
          )}
          <button
            onClick={() => setShowNewProjectForm(true)}
            style={{
              padding: "6px 14px",
              background: "#238636",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              cursor: "pointer",
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            New Project
          </button>
          <button
            onClick={handleLogout}
            style={{
              padding: "6px 12px",
              background: "transparent",
              color: "#8b949e",
              border: "1px solid #30363d",
              borderRadius: 6,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            Sign out
          </button>
        </div>
      </header>

      {/* New Project inline form */}
      {showNewProjectForm && (
        <div
          style={{
            margin: "16px 24px",
            padding: 16,
            background: "#161b22",
            border: "1px solid #30363d",
            borderRadius: 8,
          }}
        >
          <form onSubmit={handleCreateProject} style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="text"
              placeholder="Project name"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              autoFocus
              style={{
                flex: 1,
                padding: "6px 10px",
                background: "#0d1117",
                border: "1px solid #30363d",
                borderRadius: 6,
                color: "#c9d1d9",
                fontSize: 13,
              }}
            />
            <button
              type="submit"
              disabled={creating || !newProjectName.trim()}
              style={{
                padding: "6px 14px",
                background: creating ? "#1f6feb88" : "#1f6feb",
                color: "#fff",
                border: "none",
                borderRadius: 6,
                cursor: creating ? "not-allowed" : "pointer",
                fontSize: 13,
              }}
            >
              {creating ? "Creating..." : "Create"}
            </button>
            <button
              type="button"
              onClick={() => setShowNewProjectForm(false)}
              style={{
                padding: "6px 12px",
                background: "transparent",
                color: "#8b949e",
                border: "1px solid #30363d",
                borderRadius: 6,
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              Cancel
            </button>
          </form>
        </div>
      )}

      {/* Content */}
      <main style={{ padding: "24px" }}>
        {error && (
          <div
            style={{
              padding: 12,
              background: "#3d1f1f",
              border: "1px solid #da3633",
              borderRadius: 6,
              color: "#f85149",
              marginBottom: 16,
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}

        {loading ? (
          <p style={{ color: "#8b949e", fontSize: 14 }}>Loading projects...</p>
        ) : projects.length === 0 ? (
          /* Empty state */
          <div
            style={{
              textAlign: "center",
              padding: "64px 24px",
              border: "1px dashed #30363d",
              borderRadius: 12,
              maxWidth: 480,
              margin: "0 auto",
            }}
          >
            <div style={{ fontSize: 48, marginBottom: 16 }}>&#x1F4BB;</div>
            <h2 style={{ color: "#f0f6fc", marginBottom: 8, fontSize: 20 }}>
              No projects yet
            </h2>
            <p style={{ color: "#8b949e", marginBottom: 24, fontSize: 14 }}>
              Create your first project to start running ASIC flows in the browser.
            </p>
            <button
              onClick={() => setShowNewProjectForm(true)}
              style={{
                padding: "10px 20px",
                background: "#238636",
                color: "#fff",
                border: "none",
                borderRadius: 6,
                cursor: "pointer",
                fontSize: 14,
                fontWeight: 600,
              }}
            >
              Create your first project
            </button>
          </div>
        ) : (
          /* Card grid */
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: 16,
            }}
          >
            {projects.map((proj) => (
              <div
                key={proj.id}
                onClick={() => navigate(`/projects/${proj.id}`)}
                style={{
                  padding: 16,
                  background: "#161b22",
                  border: "1px solid #30363d",
                  borderRadius: 8,
                  cursor: "pointer",
                  transition: "border-color 0.15s",
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLDivElement).style.borderColor = "#1f6feb";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLDivElement).style.borderColor = "#30363d";
                }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter") navigate(`/projects/${proj.id}`);
                }}
              >
                <h3 style={{ margin: "0 0 8px 0", fontSize: 16, color: "#f0f6fc", fontWeight: 600 }}>
                  {proj.name}
                </h3>
                <div style={{ display: "flex", gap: 12, fontSize: 12, color: "#8b949e" }}>
                  <span>{proj.run_count} run{proj.run_count !== 1 ? "s" : ""}</span>
                  <span>PDK: {proj.pdk}</span>
                </div>
                <div style={{ fontSize: 11, color: "#6e7681", marginTop: 8 }}>
                  Created {new Date(proj.created_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
