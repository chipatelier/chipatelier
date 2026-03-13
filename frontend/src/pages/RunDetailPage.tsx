/**
 * RunDetailPage — tabbed run detail view.
 *
 * Locked design (from CONTEXT.md / PLAN must_haves):
 *   - Breadcrumb: Projects > {project.name} > Run #{N}
 *   - Stage status bar permanently above tabs (always visible regardless of tab)
 *   - Run/Cancel button in header area
 *   - Tabs: Logs (default during run) | Results (disabled while running, locked) | Config
 *   - Logs tab: <LogTerminal runId={runId} />
 *   - Results tab: placeholder while running; activates on completion
 *   - Auto-switch to Results tab when job completes
 *   - Poll job status every 3s when run is active; stop when terminal state
 */
import React, { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getProject as getProjectById } from "../api/projects";
import { getJobStatus, cancelJob, RunStatusResponse } from "../api/jobs";
import { LogTerminal } from "../components/LogTerminal";
import { StageStatusBar } from "../components/StageStatusBar";
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
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function isRunning(status: string | null): boolean {
    return status ? ACTIVE_STATUSES.has(status) : false;
  }

  function isTerminal(status: string | null): boolean {
    return status ? TERMINAL_STATUSES.has(status) : false;
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

        {/* Results tab */}
        {activeTab === "results" && (
          <div style={{ padding: 24 }}>
            {runStatus === "complete" && run?.ppa ? (
              <div>
                <h3 style={{ color: "#f0f6fc", fontSize: 16, marginBottom: 16 }}>PPA Metrics</h3>
                <table style={{ borderCollapse: "collapse", fontSize: 13 }}>
                  <tbody>
                    {Object.entries(run.ppa).map(([key, value]) => (
                      <tr key={key} style={{ borderBottom: "1px solid #21262d" }}>
                        <td style={{ padding: "8px 16px 8px 0", color: "#8b949e", fontWeight: 600 }}>
                          {key.replace(/_/g, " ")}
                        </td>
                        <td style={{ padding: "8px 0", color: "#c9d1d9" }}>
                          {String(value)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p style={{ color: "#8b949e", fontSize: 14 }}>
                Results will appear here when the job completes.
              </p>
            )}
          </div>
        )}

        {/* Config tab */}
        {activeTab === "config" && (
          <div style={{ padding: 24 }}>
            <h3 style={{ color: "#f0f6fc", fontSize: 16, marginBottom: 12 }}>Config Snapshot</h3>
            {run?.ppa != null ? (
              <pre
                style={{
                  background: "#161b22",
                  border: "1px solid #30363d",
                  borderRadius: 6,
                  padding: 16,
                  fontSize: 12,
                  color: "#c9d1d9",
                  overflow: "auto",
                  maxHeight: "60vh",
                }}
              >
                {JSON.stringify(run.ppa, null, 2)}
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
