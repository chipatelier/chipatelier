/**
 * RunDetailPage — tabbed run detail view.
 *
 * Locked design (from CONTEXT.md / PLAN must_haves):
 *   - Breadcrumb: Projects > {project.name} > Run #{N}
 *   - Stage status bar permanently above tabs (always visible regardless of tab)
 *   - Run/Cancel button in header area
 *   - Tabs: Logs (default during run) | Results (disabled while running, locked) | Config
 *   - Logs tab: <LogTerminal runId={runId} />
 *   - Results tab: <PpaMetricCards> + <LayoutSnapshot> — disabled while running
 *   - Config tab: raw config JSONB as formatted JSON in <pre> with copy button
 *   - Auto-switch to Results tab when job completes
 *   - Poll job status every 3s when run is active; stop when terminal state
 *   - Fetch artifacts after job completes; pass to LayoutSnapshot
 */
import React, { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getProject as getProjectById } from "../api/projects";
import { getJobStatus, cancelJob, RunStatusResponse } from "../api/jobs";
import { getArtifacts, ArtifactURLs } from "../api/artifacts";
import { LogTerminal } from "../components/LogTerminal";
import { StageStatusBar } from "../components/StageStatusBar";
import { PpaMetricCards } from "../components/PpaMetricCards";
import { LayoutSnapshot } from "../components/LayoutSnapshot";
import { useStore } from "../store";

type Tab = "logs" | "results" | "config";

const ACTIVE_STATUSES = new Set(["queued", "starting", "running"]);
const TERMINAL_STATUSES = new Set(["complete", "failed", "timeout", "cancelled"]);
const POLL_INTERVAL_MS = 3000;

export default function RunDetailPage(): React.ReactElement {
  const { id: projectId, runId } = useParams<{ id: string; runId: string }>();
  const setRunStatus = useStore((s) => s.setRunStatus);
  const setActiveRun = useStore((s) => s.setActiveRun);
  const stageProgress = useStore((s) => s.stageProgress);

  const [run, setRun] = useState<RunStatusResponse | null>(null);
  const [projectName, setProjectName] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("logs");
  const [cancelling, setCancelling] = useState(false);
  const [artifacts, setArtifacts] = useState<ArtifactURLs | null>(null);
  const [copyDone, setCopyDone] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function isRunning(status: string | null): boolean {
    return status ? ACTIVE_STATUSES.has(status) : false;
  }

  function isTerminal(status: string | null): boolean {
    return status ? TERMINAL_STATUSES.has(status) : false;
  }

  async function fetchArtifacts(id: string): Promise<void> {
    try {
      const data = await getArtifacts(id);
      setArtifacts(data);
    } catch {
      // Artifacts not yet ready — silently ignore; LayoutSnapshot shows generating state
    }
  }

  // Fetch initial run status and project name
  useEffect(() => {
    if (!runId || !projectId) return;
    Promise.all([getJobStatus(runId), getProjectById(projectId)])
      .then(([runResp, proj]) => {
        setRun(runResp);
        setProjectName(proj.name);
        setRunStatus(runResp.status, runResp.stage_completed);
        setActiveRun(runId);
        // If already complete on load, fetch artifacts immediately
        if (runResp.status === "complete") {
          fetchArtifacts(runId);
        }
      })
      .catch(() => setError("Failed to load run"))
      .finally(() => setLoading(false));

    return () => {
      setActiveRun(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, projectId]);

  // Poll status while run is active
  useEffect(() => {
    if (!runId || !run) return;
    if (isTerminal(run.status)) return;

    pollingRef.current = setInterval(async () => {
      try {
        const updated = await getJobStatus(runId);
        setRun(updated);
        setRunStatus(updated.status, updated.stage_completed);

        // Auto-switch to Results tab when job completes
        if (updated.status === "complete") {
          setActiveTab("results");
          fetchArtifacts(runId);
        }

        if (isTerminal(updated.status)) {
          if (pollingRef.current) clearInterval(pollingRef.current);
        }
      } catch {
        // Ignore polling errors — run may still be valid
      }
    }, POLL_INTERVAL_MS);

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, run?.status]);

  async function handleCancel(): Promise<void> {
    if (!runId) return;
    setCancelling(true);
    try {
      await cancelJob(runId);
      const updated = await getJobStatus(runId);
      setRun(updated);
      setRunStatus(updated.status, updated.stage_completed);
    } catch {
      setError("Failed to cancel run");
    } finally {
      setCancelling(false);
    }
  }

  function handleCopyConfig(): void {
    const configText = run?.config ? JSON.stringify(run.config, null, 2) : "";
    navigator.clipboard.writeText(configText).then(() => {
      setCopyDone(true);
      setTimeout(() => setCopyDone(false), 2000);
    });
  }

  if (loading) {
    return (
      <div style={{ fontFamily: "sans-serif", padding: 24, color: "#8b949e", background: "#0d1117", minHeight: "100vh" }}>
        Loading...
      </div>
    );
  }

  const runStatus = run?.status ?? null;
  const running = isRunning(runStatus);

  return (
    <div
      style={{
        fontFamily: "sans-serif",
        minHeight: "100vh",
        background: "#0d1117",
        color: "#c9d1d9",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header */}
      <header style={{ padding: "16px 24px", borderBottom: "1px solid #30363d", background: "#161b22", flexShrink: 0 }}>
        {/* Breadcrumb */}
        <nav style={{ fontSize: 13, color: "#8b949e", marginBottom: 8 }}>
          <Link to="/projects" style={{ color: "#58a6ff", textDecoration: "none" }}>Projects</Link>
          <span style={{ margin: "0 8px" }}>&rsaquo;</span>
          <Link
            to={`/projects/${projectId}`}
            style={{ color: "#58a6ff", textDecoration: "none" }}
          >
            {projectName || "Project"}
          </Link>
          <span style={{ margin: "0 8px" }}>&rsaquo;</span>
          <span style={{ color: "#f0f6fc" }}>Run {run?.id?.slice(0, 8) ?? "..."}</span>
        </nav>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <h2 style={{ margin: 0, fontSize: 18, color: "#f0f6fc" }}>
              Run Detail
            </h2>
            {runStatus && (
              <span
                style={{
                  fontSize: 11,
                  padding: "2px 8px",
                  borderRadius: 12,
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  background: running ? "#1f3a5f" : runStatus === "complete" ? "#1f4022" : "#3d1f1f",
                  color: running ? "#58a6ff" : runStatus === "complete" ? "#3fb950" : "#f85149",
                }}
              >
                {runStatus}
              </span>
            )}
          </div>
          {running && (
            <button
              onClick={handleCancel}
              disabled={cancelling}
              style={{
                padding: "6px 14px",
                background: cancelling ? "#21262d" : "#da3633",
                color: cancelling ? "#6e7681" : "#fff",
                border: "none",
                borderRadius: 6,
                cursor: cancelling ? "not-allowed" : "pointer",
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              {cancelling ? "Cancelling..." : "Cancel Run"}
            </button>
          )}
        </div>
      </header>

      {/* Stage status bar — permanently visible above tabs */}
      <StageStatusBar stageProgress={stageProgress} />

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          gap: 0,
          borderBottom: "1px solid #30363d",
          background: "#161b22",
          flexShrink: 0,
        }}
      >
        {(["logs", "results", "config"] as Tab[]).map((tab) => {
          const disabled = tab === "results" && running;
          const active = activeTab === tab;
          return (
            <button
              key={tab}
              onClick={() => !disabled && setActiveTab(tab)}
              disabled={disabled}
              style={{
                padding: "10px 20px",
                border: "none",
                borderBottom: active ? "2px solid #1f6feb" : "2px solid transparent",
                background: "transparent",
                color: disabled ? "#6e7681" : active ? "#f0f6fc" : "#8b949e",
                cursor: disabled ? "not-allowed" : "pointer",
                fontSize: 13,
                fontWeight: active ? 600 : 400,
                textTransform: "capitalize",
              }}
              title={disabled ? "Results will appear when the job completes" : undefined}
            >
              {tab}
              {tab === "results" && running && (
                <span style={{ fontSize: 10, marginLeft: 4, color: "#6e7681" }}>
                  (locked)
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {error && (
          <div style={{ padding: 12, background: "#3d1f1f", border: "1px solid #da3633", borderRadius: 6, color: "#f85149", margin: 16, fontSize: 13 }}>
            {error}
          </div>
        )}

        {/* Logs tab */}
        {activeTab === "logs" && (
          <div style={{ flex: 1, overflow: "hidden", minHeight: 0 }}>
            <LogTerminal runId={runId ?? null} isRunning={running} />
          </div>
        )}

        {/* Results tab — disabled while running (LOCKED) */}
        {activeTab === "results" && (
          <div style={{ padding: 24, overflowY: "auto" }}>
            {runStatus === "complete" ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
                {/* PPA Metric Cards */}
                <div>
                  <h3 style={{ color: "#f0f6fc", fontSize: 15, margin: "0 0 16px 0" }}>
                    PPA Metrics
                  </h3>
                  <PpaMetricCards metrics={run?.ppa as import("../components/PpaMetricCards").PpaMetrics | null} runId={runId} />
                </div>

                {/* Layout Snapshot with VNC button and download links */}
                <div>
                  <h3 style={{ color: "#f0f6fc", fontSize: 15, margin: "0 0 16px 0" }}>
                    Layout Preview
                  </h3>
                  <LayoutSnapshot
                    runId={runId ?? ""}
                    artifacts={runStatus === "complete" ? artifacts : null}
                  />
                </div>
              </div>
            ) : (
              <p style={{ color: "#8b949e", fontSize: 14 }}>
                Results will appear here when the job completes.
              </p>
            )}
          </div>
        )}

        {/* Config tab — raw config JSONB with copy button */}
        {activeTab === "config" && (
          <div style={{ padding: 24, overflowY: "auto" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
              <h3 style={{ color: "#f0f6fc", fontSize: 15, margin: 0 }}>Config Snapshot</h3>
              {run?.config && (
                <button
                  onClick={handleCopyConfig}
                  style={{
                    padding: "4px 10px",
                    background: copyDone ? "#1f4022" : "#21262d",
                    color: copyDone ? "#3fb950" : "#8b949e",
                    border: "1px solid #30363d",
                    borderRadius: 6,
                    cursor: "pointer",
                    fontSize: 12,
                    fontWeight: 500,
                  }}
                >
                  {copyDone ? "Copied!" : "Copy"}
                </button>
              )}
            </div>
            {run?.config != null ? (
              <pre
                style={{
                  background: "#161b22",
                  border: "1px solid #30363d",
                  borderRadius: 6,
                  padding: 16,
                  fontSize: 12,
                  fontFamily: "monospace",
                  color: "#c9d1d9",
                  overflow: "auto",
                  maxHeight: "60vh",
                  margin: 0,
                }}
              >
                {JSON.stringify(run.config, null, 2)}
              </pre>
            ) : (
              <p style={{ color: "#8b949e", fontSize: 13 }}>
                No config snapshot available for this run.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
