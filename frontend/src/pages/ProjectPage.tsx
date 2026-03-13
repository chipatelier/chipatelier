/**
 * ProjectPage — shows run list table for a project.
 *
 * Locked design (from CONTEXT.md / PLAN must_haves):
 *   - Breadcrumb: Projects > {project.name}
 *   - Run table: Status, Target Stage, Stage Completed, Created At, WNS, DRC columns
 *   - Click row → navigate to run detail
 *   - "New Run" button disabled when active run exists (only one active run per project)
 *   - File upload section for Verilog + config.mk
 */
import React, { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { getProject, listRuns, uploadFiles, ProjectResponse, RunSummary } from "../api/projects";
import { submitJob } from "../api/jobs";
import { RunHistoryTable } from "../components/RunHistoryTable";

const ACTIVE_STATUSES = new Set(["queued", "starting", "running"]);

const STAGES = [
  { value: "synth",     label: "Synthesis" },
  { value: "floorplan", label: "Floorplan" },
  { value: "place",     label: "Placement" },
  { value: "cts",       label: "CTS" },
  { value: "route",     label: "Route" },
  { value: "gds",       label: "GDS (full flow)" },
];

export default function ProjectPage(): React.ReactElement {
  const { id: projectId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [targetStage, setTargetStage] = useState("route");
  const [uploadFiles_, setUploadFiles_] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [sourcePath, setSourcePath] = useState<string | null>(null);

  const hasActiveRun = runs.some((r) => ACTIVE_STATUSES.has(r.status));

  useEffect(() => {
    if (!projectId) return;
    Promise.all([getProject(projectId), listRuns(projectId)])
      .then(([proj, runList]) => {
        setProject(proj);
        setRuns(runList);
      })
      .catch(() => setError("Failed to load project"))
      .finally(() => setLoading(false));
  }, [projectId]);

  async function handleNewRun(): Promise<void> {
    if (!projectId || hasActiveRun) return;
    setSubmitting(true);
    setError(null);
    try {
      const resp = await submitJob({
        project_id: projectId,
        target_stage: targetStage,
        source_path: sourcePath || undefined,  // Pass source_path from last upload
      });
      // Refresh runs list and navigate to new run
      const updated = await listRuns(projectId);
      setRuns(updated);
      navigate(`/projects/${projectId}/runs/${resp.run_id}`);
    } catch {
      setError("Failed to submit run. Make sure files are uploaded first.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUpload(): Promise<void> {
    if (!projectId || uploadFiles_.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const uploadResp = await uploadFiles(projectId, uploadFiles_);
      setSourcePath(uploadResp.source_path);  // Save source_path for next run
      setUploadFiles_([]);
      // Refresh runs to pick up any status changes
      const updated = await listRuns(projectId);
      setRuns(updated);
    } catch {
      setError("File upload failed.");
    } finally {
      setUploading(false);
    }
  }

  if (loading) {
    return (
      <div style={{ fontFamily: "sans-serif", padding: 24, color: "#8b949e", background: "#0d1117", minHeight: "100vh" }}>
        Loading...
      </div>
    );
  }

  return (
    <div style={{ fontFamily: "sans-serif", minHeight: "100vh", background: "#0d1117", color: "#c9d1d9" }}>
      {/* Header */}
      <header style={{ padding: "16px 24px", borderBottom: "1px solid #30363d", background: "#161b22" }}>
        {/* Breadcrumb */}
        <nav style={{ fontSize: 13, color: "#8b949e", marginBottom: 8 }}>
          <Link to="/projects" style={{ color: "#58a6ff", textDecoration: "none" }}>
            Projects
          </Link>
          <span style={{ margin: "0 8px" }}>&rsaquo;</span>
          <span style={{ color: "#f0f6fc" }}>{project?.name ?? "..."}</span>
        </nav>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0, fontSize: 20, color: "#f0f6fc" }}>{project?.name}</h2>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <select
              value={targetStage}
              onChange={(e) => setTargetStage(e.target.value)}
              disabled={hasActiveRun || submitting}
              title="Target flow stage"
              style={{
                padding: "6px 10px",
                background: "#161b22",
                color: hasActiveRun || submitting ? "#6e7681" : "#c9d1d9",
                border: "1px solid #30363d",
                borderRadius: 6,
                fontSize: 13,
                cursor: hasActiveRun || submitting ? "not-allowed" : "pointer",
              }}
            >
              {STAGES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
            <button
              onClick={handleNewRun}
              disabled={hasActiveRun || submitting}
              title={hasActiveRun ? "Cancel the active run before starting a new one" : "Start a new ORFS run"}
              style={{
                padding: "6px 14px",
                background: hasActiveRun || submitting ? "#21262d" : "#238636",
                color: hasActiveRun || submitting ? "#6e7681" : "#fff",
                border: `1px solid ${hasActiveRun || submitting ? "#30363d" : "transparent"}`,
                borderRadius: 6,
                cursor: hasActiveRun || submitting ? "not-allowed" : "pointer",
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              {submitting ? "Submitting..." : hasActiveRun ? "Run Active" : "New Run"}
            </button>
          </div>
        </div>
      </header>

      <main style={{ padding: 24 }}>
        {error && (
          <div style={{ padding: 12, background: "#3d1f1f", border: "1px solid #da3633", borderRadius: 6, color: "#f85149", marginBottom: 16, fontSize: 13 }}>
            {error}
          </div>
        )}

        {/* File upload section */}
        <section style={{ marginBottom: 24, padding: 16, background: "#161b22", border: "1px solid #30363d", borderRadius: 8 }}>
          <h3 style={{ margin: "0 0 12px 0", fontSize: 14, color: "#f0f6fc" }}>Upload Design Files</h3>
          <p style={{ fontSize: 12, color: "#8b949e", margin: "0 0 12px 0" }}>
            Upload Verilog (.v) and config.mk files. The uploaded version will be used for the next run.
          </p>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <input
              type="file"
              multiple
              accept=".v,.sv,.mk"
              onChange={(e) => setUploadFiles_(Array.from(e.target.files ?? []))}
              style={{ fontSize: 13, color: "#c9d1d9" }}
            />
            {uploadFiles_.length > 0 && (
              <button
                onClick={handleUpload}
                disabled={uploading}
                style={{
                  padding: "6px 14px",
                  background: uploading ? "#21262d" : "#1f6feb",
                  color: uploading ? "#6e7681" : "#fff",
                  border: "none",
                  borderRadius: 6,
                  cursor: uploading ? "not-allowed" : "pointer",
                  fontSize: 13,
                }}
              >
                {uploading ? "Uploading..." : `Upload ${uploadFiles_.length} file${uploadFiles_.length !== 1 ? "s" : ""}`}
              </button>
            )}
          </div>
        </section>

        {/* Runs table — RSLT-04 */}
        <section>
          <h3 style={{ margin: "0 0 12px 0", fontSize: 14, color: "#f0f6fc" }}>
            Runs ({runs.length})
          </h3>
          <RunHistoryTable runs={runs} projectId={projectId ?? ""} />
        </section>
      </main>
    </div>
  );
}
