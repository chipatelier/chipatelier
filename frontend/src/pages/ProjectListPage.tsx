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
import { listProjects, createProject, deleteProject, updateProject, ProjectResponse } from "../api/projects";
import { AppHeader } from "../components/AppHeader/AppHeader";
import { ChangePasswordModal } from "../components/ChangePasswordModal/ChangePasswordModal";

export default function ProjectListPage(): React.ReactElement {
  const navigate = useNavigate();

  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewProjectForm, setShowNewProjectForm] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [creating, setCreating] = useState(false);
  const [changePwOpen, setChangePwOpen] = useState(false);
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<ProjectResponse | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch(() => setError("Failed to load projects"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    function handleClickOutside() { setMenuOpenId(null); }
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, []);

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

  async function handleRename(proj: ProjectResponse): Promise<void> {
    if (!renameValue.trim() || renameValue.trim() === proj.name) {
      setRenamingId(null);
      return;
    }
    try {
      const updated = await updateProject(proj.id, { name: renameValue.trim() });
      setProjects((prev) => prev.map((p) => (p.id === proj.id ? updated : p)));
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Rename failed");
    } finally {
      setRenamingId(null);
    }
  }

  async function handleDelete(): Promise<void> {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteProject(deleteTarget.id);
      setProjects((prev) => prev.filter((p) => p.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err: any) {
      setDeleteError(err?.response?.data?.detail ?? "Delete failed");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div style={{ fontFamily: "sans-serif", minHeight: "100vh", background: "#0d1117", color: "#c9d1d9" }}>
      <AppHeader
        actions={
          <button
            style={{
              borderRadius: 6,
              background: "#238636",
              color: "#fff",
              padding: "8px 14px",
              fontSize: 13,
              fontWeight: 600,
              border: "none",
              cursor: "pointer",
            }}
            onClick={() => setShowNewProjectForm(true)}
          >
            + New Project
          </button>
        }
        onChangePassword={() => setChangePwOpen(true)}
      />
      <ChangePasswordModal open={changePwOpen} onClose={() => setChangePwOpen(false)} />

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
              <div key={proj.id} style={{ position: "relative" }}>
                {/* Kebab button */}
                <button
                  onClick={(e) => { e.stopPropagation(); setMenuOpenId(menuOpenId === proj.id ? null : proj.id); }}
                  style={{ position: "absolute", top: 8, right: 8, background: "transparent", border: "none", color: "#8b949e", cursor: "pointer", padding: "2px 6px", fontSize: 18, zIndex: 1, lineHeight: 1 }}
                  aria-label="Project options"
                >⋮</button>

                {menuOpenId === proj.id && (
                  <div style={{ position: "absolute", top: 32, right: 8, background: "#161b22", border: "1px solid #30363d", borderRadius: 6, zIndex: 10, minWidth: 120, boxShadow: "0 4px 12px rgba(0,0,0,0.4)" }}>
                    <button
                      onClick={(e) => { e.stopPropagation(); setRenamingId(proj.id); setRenameValue(proj.name); setMenuOpenId(null); }}
                      style={{ display: "block", width: "100%", padding: "8px 12px", background: "none", border: "none", color: "#c9d1d9", cursor: "pointer", fontSize: 13, textAlign: "left" as const }}
                    >Rename</button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setDeleteTarget(proj); setMenuOpenId(null); }}
                      style={{ display: "block", width: "100%", padding: "8px 12px", background: "none", border: "none", color: "#f85149", cursor: "pointer", fontSize: 13, textAlign: "left" as const }}
                    >Delete</button>
                  </div>
                )}

                {/* Card */}
                <div
                  onClick={() => renamingId !== proj.id && navigate(`/projects/${proj.id}`)}
                  style={{
                    padding: 16,
                    background: "#161b22",
                    border: "1px solid #30363d",
                    borderRadius: 8,
                    cursor: renamingId === proj.id ? "default" : "pointer",
                    transition: "border-color 0.15s",
                  }}
                  onMouseEnter={(e) => {
                    if (renamingId !== proj.id) (e.currentTarget as HTMLDivElement).style.borderColor = "#1f6feb";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLDivElement).style.borderColor = "#30363d";
                  }}
                >
                  {renamingId === proj.id ? (
                    <input
                      type="text"
                      autoFocus
                      value={renameValue}
                      onChange={(e) => setRenameValue(e.target.value)}
                      onBlur={() => handleRename(proj)}
                      onKeyDown={(e) => { if (e.key === "Enter") handleRename(proj); if (e.key === "Escape") setRenamingId(null); }}
                      onClick={(e) => e.stopPropagation()}
                      style={{ width: "100%", padding: "4px 8px", background: "#0d1117", border: "1px solid #1f6feb", borderRadius: 4, color: "#f0f6fc", fontSize: 15, fontWeight: 600, boxSizing: "border-box" as const }}
                    />
                  ) : (
                    <h3 style={{ margin: "0 0 8px 0", fontSize: 16, color: "#f0f6fc", fontWeight: 600, paddingRight: 24 }}>{proj.name}</h3>
                  )}
                  <div style={{ display: "flex", gap: 12, fontSize: 12, color: "#8b949e" }}>
                    <span>{proj.run_count} run{proj.run_count !== 1 ? "s" : ""}</span>
                    <span>PDK: {proj.pdk}</span>
                  </div>
                  <div style={{ fontSize: 11, color: "#6e7681", marginTop: 8 }}>
                    Created {new Date(proj.created_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {deleteTarget && (
          <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 24, width: 400, maxWidth: "90vw" }}>
              <h3 style={{ margin: "0 0 12px 0", color: "#f0f6fc", fontSize: 16 }}>Delete {deleteTarget.name}?</h3>
              <p style={{ color: "#8b949e", fontSize: 13, margin: "0 0 16px 0" }}>
                This will permanently delete {deleteTarget.run_count} run{deleteTarget.run_count !== 1 ? "s" : ""} and free {(deleteTarget.storage_bytes / 1e9).toFixed(1)} GB of storage. This cannot be undone.
              </p>
              {deleteError && <p style={{ color: "#f85149", fontSize: 12, margin: "0 0 12px 0" }}>{deleteError}</p>}
              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                <button onClick={() => { setDeleteTarget(null); setDeleteError(null); }} style={{ padding: "6px 14px", background: "transparent", color: "#8b949e", border: "1px solid #30363d", borderRadius: 6, cursor: "pointer", fontSize: 13 }}>Cancel</button>
                <button onClick={handleDelete} disabled={deleting} style={{ padding: "6px 14px", background: "#da3633", color: "#fff", border: "none", borderRadius: 6, cursor: deleting ? "not-allowed" : "pointer", fontSize: 13, fontWeight: 600 }}>
                  {deleting ? "Deleting…" : "Delete Project"}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
