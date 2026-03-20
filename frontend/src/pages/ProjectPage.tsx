/**
 * ProjectPage — 3-tab layout: Runs | Files & Config | Settings
 */
import React, { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { getProject, listRuns, deleteProject, updateProject, ProjectResponse, RunSummary } from "../api/projects";
import { RunHistoryTable } from "../components/RunHistoryTable";
import { AppHeader } from "../components/AppHeader/AppHeader";
import { ChangePasswordModal } from "../components/ChangePasswordModal/ChangePasswordModal";
import NewRunModal from "../components/NewRunModal/NewRunModal";
import FileConfigTab from "../components/FileConfigTab/FileConfigTab";

type Tab = "runs" | "files" | "settings";

const ACTIVE_STATUSES = new Set(["queued", "starting", "running"]);

export default function ProjectPage(): React.ReactElement {
  const { id: projectId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [tab, setTab] = useState<Tab>("runs");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [changePwOpen, setChangePwOpen] = useState(false);

  const hasActiveRun = runs.some((r) => ACTIVE_STATUSES.has(r.status));

  async function refresh(): Promise<void> {
    if (!projectId) return;
    const [proj, runList] = await Promise.all([getProject(projectId), listRuns(projectId)]);
    setProject(proj);
    setRuns(runList);
  }

  useEffect(() => {
    if (!projectId) return;
    refresh()
      .catch(() => setError("Failed to load project"))
      .finally(() => setLoading(false));
  }, [projectId]);

  function handleRunSubmitted(runId: string): void {
    refresh().then(() => navigate(`/projects/${projectId}/runs/${runId}`));
  }

  const tabStyle = (t: Tab): React.CSSProperties => ({
    padding: "8px 16px", cursor: "pointer", fontSize: 13, fontWeight: 500,
    color: tab === t ? "#58a6ff" : "#8b949e",
    borderBottom: tab === t ? "2px solid #58a6ff" : "2px solid transparent",
    background: "none", border: "none", marginBottom: -1,
  });

  if (loading) return <div style={{ padding: 24, color: "#8b949e", background: "#0d1117", minHeight: "100vh" }}>Loading…</div>;

  return (
    <div style={{ fontFamily: "sans-serif", minHeight: "100vh", background: "#0d1117", color: "#c9d1d9" }}>
      <AppHeader
        breadcrumbs={
          <span>
            <Link to="/projects" style={{ color: "#58a6ff", textDecoration: "none" }}>Projects</Link>
            {" › "}
            <span style={{ color: "#e6edf3" }}>{project?.name ?? "…"}</span>
          </span>
        }
        onChangePassword={() => setChangePwOpen(true)}
      />
      <ChangePasswordModal open={changePwOpen} onClose={() => setChangePwOpen(false)} />

      {/* Tab bar */}
      <div style={{ padding: "0 24px", borderBottom: "1px solid #30363d", background: "#161b22", display: "flex", gap: 4 }}>
        <button style={tabStyle("runs")} onClick={() => setTab("runs")}>Runs</button>
        <button style={tabStyle("files")} onClick={() => setTab("files")}>Files &amp; Config</button>
        <button style={tabStyle("settings")} onClick={() => setTab("settings")}>Settings</button>
      </div>

      {error && (
        <div style={{ margin: "16px 24px", padding: 12, background: "#3d1f1f", border: "1px solid #da3633", borderRadius: 6, color: "#f85149", fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* Runs tab */}
      {tab === "runs" && project && (
        <main style={{ padding: 24 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
            <NewRunModal project={project} hasActiveRun={hasActiveRun} onSubmitted={handleRunSubmitted} />
          </div>
          <RunHistoryTable runs={runs} projectId={projectId ?? ""} />
        </main>
      )}

      {/* Files & Config tab */}
      {tab === "files" && project && (
        <FileConfigTab project={project} onProjectUpdate={(updated) => setProject(updated)} />
      )}

      {/* Settings tab */}
      {tab === "settings" && project && (
        <SettingsTab project={project} onProjectUpdate={setProject} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Settings tab — inline rename + danger zone
// ---------------------------------------------------------------------------

function SettingsTab({ project, onProjectUpdate }: { project: ProjectResponse; onProjectUpdate: (p: ProjectResponse) => void }): React.ReactElement {
  const navigate = useNavigate();
  const [name, setName] = useState(project.name);
  const [renaming, setRenaming] = useState(false);
  const [renameError, setRenameError] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function handleRename(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    if (name.trim() === project.name) return;
    setRenaming(true);
    setRenameError(null);
    try {
      const updated = await updateProject(project.id, { name: name.trim() });
      onProjectUpdate(updated);
    } catch (err: any) {
      setRenameError(err?.response?.data?.detail ?? "Rename failed");
    } finally {
      setRenaming(false);
    }
  }

  async function handleDelete(): Promise<void> {
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteProject(project.id);
      navigate("/projects");
    } catch (err: any) {
      setDeleteError(err?.response?.data?.detail ?? "Delete failed");
      setDeleting(false);
    }
  }

  const gbUsed = (project.storage_bytes / 1e9).toFixed(1);

  return (
    <main style={{ padding: 24, maxWidth: 600 }}>
      <section style={{ marginBottom: 32 }}>
        <h3 style={{ margin: "0 0 12px 0", fontSize: 15, color: "#f0f6fc" }}>Project Name</h3>
        <form onSubmit={handleRename} style={{ display: "flex", gap: 8 }}>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ flex: 1, padding: "6px 10px", background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, color: "#c9d1d9", fontSize: 13 }}
          />
          <button
            type="submit"
            disabled={renaming || name.trim() === project.name}
            style={{ padding: "6px 14px", background: "#1f6feb", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13 }}
          >
            {renaming ? "Saving…" : "Save"}
          </button>
        </form>
        {renameError && <p style={{ color: "#f85149", fontSize: 12, marginTop: 6 }}>{renameError}</p>}
      </section>

      <section style={{ border: "1px solid #da363344", borderRadius: 8, padding: 16 }}>
        <h3 style={{ margin: "0 0 8px 0", fontSize: 15, color: "#f85149" }}>Danger Zone</h3>
        <p style={{ fontSize: 13, color: "#8b949e", margin: "0 0 12px 0" }}>
          This project uses {gbUsed} GB of storage. Deletion is permanent.
        </p>
        {!showDeleteConfirm ? (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            style={{ padding: "6px 14px", background: "transparent", color: "#f85149", border: "1px solid #da3633", borderRadius: 6, cursor: "pointer", fontSize: 13 }}
          >
            Delete Project…
          </button>
        ) : (
          <div style={{ background: "#3d1f1f", border: "1px solid #da3633", borderRadius: 6, padding: 12 }}>
            <p style={{ fontSize: 13, color: "#f0f6fc", margin: "0 0 8px 0" }}>
              Delete <strong>{project.name}</strong>? This will permanently delete {project.run_count} run{project.run_count !== 1 ? "s" : ""} and free {gbUsed} GB. This cannot be undone.
            </p>
            {deleteError && <p style={{ color: "#f85149", fontSize: 12, margin: "0 0 8px 0" }}>{deleteError}</p>}
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={handleDelete}
                disabled={deleting}
                style={{ padding: "6px 14px", background: "#da3633", color: "#fff", border: "none", borderRadius: 6, cursor: deleting ? "not-allowed" : "pointer", fontSize: 13, fontWeight: 600 }}
              >
                {deleting ? "Deleting…" : "Delete Project"}
              </button>
              <button
                onClick={() => { setShowDeleteConfirm(false); setDeleteError(null); }}
                style={{ padding: "6px 14px", background: "transparent", color: "#8b949e", border: "1px solid #30363d", borderRadius: 6, cursor: "pointer", fontSize: 13 }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
