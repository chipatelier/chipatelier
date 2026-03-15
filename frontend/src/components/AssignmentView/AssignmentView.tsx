/**
 * AssignmentView — student-facing assignment interface.
 *
 * Tabs:
 *   Instructions — renders assignment description.
 *   Submit       — run picker, submit button, grade result via WebSocket.
 *   Leaderboard  — placeholder (implemented in plan 02-06).
 *
 * Grade flow:
 *   1. Student picks a completed run from run picker.
 *   2. CheckpointCards shows live preview (client-side, no submission yet).
 *   3. Student clicks "Submit for Grading".
 *   4. Optimistic banner: "Submitted — grading in progress..."
 *   5. useGradeStream connects to WS endpoint.
 *   6. When grade arrives, CheckpointCards switches to result mode.
 */
import { useState, useEffect } from "react";
import { Assignment } from "../../store/courseSlice";
import { CheckpointCards } from "../CheckpointCards";
import { useGradeStream } from "../../hooks/useGradeStream";
import { submitRun, getMySubmissions, getPreviewScore, SubmissionResponse } from "../../api/submissions";
import { getLeaderboard, LeaderboardEntry } from "../../api/courses";

interface Props {
  assignment: Assignment;
  currentUserId: string;
}

type Tab = "instructions" | "submit" | "leaderboard";

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function TabBar({
  active,
  onChange,
}: {
  active: Tab;
  onChange: (tab: Tab) => void;
}) {
  const tabs: { key: Tab; label: string }[] = [
    { key: "instructions", label: "Instructions" },
    { key: "submit", label: "Submit" },
    { key: "leaderboard", label: "Leaderboard" },
  ];

  return (
    <div
      style={{
        display: "flex",
        borderBottom: "1px solid #30363d",
        marginBottom: 24,
        gap: 0,
      }}
    >
      {tabs.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          style={{
            background: "none",
            border: "none",
            borderBottom: active === key ? "2px solid #58a6ff" : "2px solid transparent",
            color: active === key ? "#f0f6fc" : "#8b949e",
            cursor: "pointer",
            fontSize: 14,
            fontWeight: active === key ? 600 : 400,
            padding: "8px 16px",
            marginBottom: -1,
            transition: "color 0.1s",
          }}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function InstructionsTab({ assignment }: { assignment: Assignment }) {
  if (!assignment.description) {
    return (
      <div style={{ color: "#6e7681", fontStyle: "italic", fontSize: 14 }}>
        No instructions provided for this assignment.
      </div>
    );
  }
  return (
    <div
      style={{
        color: "#c9d1d9",
        fontSize: 14,
        lineHeight: 1.6,
        whiteSpace: "pre-wrap",
      }}
    >
      {assignment.description}
    </div>
  );
}

interface SubmitTabProps {
  assignment: Assignment;
  currentUserId: string;
}

function SubmitTab({ assignment, currentUserId: _currentUserId }: SubmitTabProps) {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [previewPpa, setPreviewPpa] = useState<Record<string, number | null>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submittedRunId, setSubmittedRunId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pastSubmissions, setPastSubmissions] = useState<SubmissionResponse[]>([]);

  // Grade stream — connects when submittedRunId is set
  const { gradeResult, isConnected: gradeConnected } = useGradeStream(submittedRunId);

  // Load completed runs (all projects) — simplified: user needs project_id
  // In a full implementation this would come from a project context
  // For now, show a message to select a project/run
  useEffect(() => {
    // Load past submissions for this assignment
    getMySubmissions(assignment.id)
      .then(setPastSubmissions)
      .catch(() => setPastSubmissions([]));
  }, [assignment.id]);

  // Load preview when run selected
  useEffect(() => {
    if (!selectedRunId) {
      setPreviewPpa({});
      return;
    }
    getPreviewScore(assignment.id, selectedRunId)
      .then(() => {
        // Server-side preview handled by CheckpointCards in preview mode
        setPreviewPpa({});
      })
      .catch(() => setPreviewPpa({}));
  }, [selectedRunId, assignment.id]);

  const handleSubmit = async () => {
    if (!selectedRunId) return;
    setSubmitting(true);
    setError(null);
    try {
      await submitRun(assignment.id, selectedRunId);
      setSubmittedRunId(selectedRunId);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(
        axiosErr.response?.data?.detail ?? axiosErr.message ?? "Submission failed"
      );
    } finally {
      setSubmitting(false);
    }
  };

  const isGrading = submittedRunId && !gradeResult;
  const isComplete = submittedRunId && gradeResult;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Run picker */}
      {!submittedRunId && (
        <div>
          <label
            style={{ fontSize: 12, color: "#8b949e", fontWeight: 600, display: "block", marginBottom: 8 }}
          >
            SELECT RUN
          </label>
          <input
            type="text"
            placeholder="Paste run ID to submit..."
            value={selectedRunId ?? ""}
            onChange={(e) => setSelectedRunId(e.target.value || null)}
            style={{
              background: "#0d1117",
              border: "1px solid #30363d",
              borderRadius: 6,
              color: "#c9d1d9",
              fontSize: 14,
              padding: "8px 12px",
              width: "100%",
              boxSizing: "border-box",
            }}
          />
          <div style={{ fontSize: 12, color: "#6e7681", marginTop: 4 }}>
            Enter the run ID from your project's run history.
          </div>
        </div>
      )}

      {/* Live checkpoint preview (before submission) */}
      {selectedRunId && !submittedRunId && (
        <div>
          <div style={{ fontSize: 13, color: "#8b949e", marginBottom: 12 }}>
            Checkpoint Preview
          </div>
          <CheckpointCards
            checkpointRules={assignment.checkpoint_rules}
            ppa={previewPpa}
          />
          <button
            onClick={handleSubmit}
            disabled={submitting}
            style={{
              marginTop: 16,
              background: submitting ? "#30363d" : "#238636",
              border: "1px solid",
              borderColor: submitting ? "#30363d" : "#2ea043",
              borderRadius: 6,
              color: submitting ? "#6e7681" : "#ffffff",
              cursor: submitting ? "not-allowed" : "pointer",
              fontSize: 14,
              fontWeight: 600,
              padding: "10px 20px",
              width: "100%",
            }}
          >
            {submitting ? "Submitting..." : "Submit for Grading"}
          </button>
          {error && (
            <div
              style={{
                marginTop: 8,
                color: "#f85149",
                fontSize: 13,
                background: "#3d1f1f",
                border: "1px solid #6e4040",
                borderRadius: 6,
                padding: "8px 12px",
              }}
            >
              {error}
            </div>
          )}
        </div>
      )}

      {/* Grading in progress */}
      {isGrading && (
        <div
          style={{
            background: "#1f2d3d",
            border: "1px solid #1f4022",
            borderRadius: 8,
            padding: "16px",
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <span style={{ fontSize: 16 }}>⏳</span>
          <div>
            <div style={{ color: "#58a6ff", fontWeight: 600, fontSize: 14 }}>
              Submitted — grading in progress...
            </div>
            <div style={{ color: "#8b949e", fontSize: 12, marginTop: 4 }}>
              {gradeConnected
                ? "Connected to grading service."
                : "Connecting to grading service..."}
            </div>
          </div>
        </div>
      )}

      {/* Grade result */}
      {isComplete && gradeResult && (
        <div>
          <div
            style={{
              background: "#1f4022",
              border: "1px solid #2ea043",
              borderRadius: 8,
              padding: "12px 16px",
              marginBottom: 16,
              color: "#3fb950",
              fontWeight: 600,
              fontSize: 14,
            }}
          >
            Grading complete!
          </div>
          <CheckpointCards
            checkpointRules={assignment.checkpoint_rules}
            ppa={{}}
            gradeResult={gradeResult}
          />
        </div>
      )}

      {/* Past submissions */}
      {pastSubmissions.length > 0 && (
        <div>
          <div
            style={{
              fontSize: 13,
              color: "#8b949e",
              fontWeight: 600,
              marginBottom: 8,
              textTransform: "uppercase",
            }}
          >
            Past Submissions
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {pastSubmissions.map((sub) => (
              <div
                key={sub.id}
                style={{
                  background: "#0d1117",
                  border: "1px solid #30363d",
                  borderRadius: 6,
                  padding: "8px 12px",
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 13,
                }}
              >
                <span style={{ color: "#6e7681" }}>
                  {new Date(sub.submitted_at).toLocaleString()}
                </span>
                <span style={{ color: sub.score !== null ? "#3fb950" : "#6e7681" }}>
                  {sub.score !== null ? `${sub.score} pts` : sub.grading_status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// LeaderboardTab
// ---------------------------------------------------------------------------

function LeaderboardTab({
  assignment,
  currentUserId,
}: {
  assignment: Assignment;
  currentUserId: string;
}) {
  const [entries, setEntries] = useState<LeaderboardEntry[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getLeaderboard(assignment.id)
      .then(setEntries)
      .catch(() => setError("Failed to load leaderboard"))
      .finally(() => setLoading(false));
  }, [assignment.id]);

  if (loading) {
    return (
      <div style={{ color: "#8b949e", fontSize: 14 }}>Loading leaderboard...</div>
    );
  }

  if (error) {
    return <div style={{ color: "#f85149", fontSize: 14 }}>{error}</div>;
  }

  if (!entries || entries.length === 0) {
    return (
      <div style={{ color: "#6e7681", fontStyle: "italic", fontSize: 14 }}>
        No submissions yet. Be the first to submit!
      </div>
    );
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table
        style={{
          borderCollapse: "collapse",
          fontSize: 13,
          width: "100%",
        }}
      >
        <thead>
          <tr
            style={{
              background: "#161b22",
              borderBottom: "1px solid #30363d",
            }}
          >
            {["Rank", "Score", "WNS (ns)"].map((col) => (
              <th
                key={col}
                style={{
                  color: "#8b949e",
                  fontSize: 11,
                  fontWeight: 600,
                  letterSpacing: "0.04em",
                  padding: "8px 12px",
                  textAlign: col === "Rank" ? "center" : "right",
                  textTransform: "uppercase",
                }}
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => {
            const isSelf = entry.is_self || entry.user_id === currentUserId;
            return (
              <tr
                key={entry.user_id}
                style={{
                  background: isSelf ? "#1f2d3d" : entry.rank % 2 === 0 ? "#161b22" : "#0d1117",
                  borderTop: "1px solid #1c2128",
                  borderLeft: isSelf ? "2px solid #58a6ff" : "2px solid transparent",
                }}
              >
                <td
                  style={{
                    color: "#8b949e",
                    fontWeight: 600,
                    padding: "8px 12px",
                    textAlign: "center",
                  }}
                >
                  {isSelf ? (
                    <span>
                      #{entry.rank}{" "}
                      <span
                        style={{
                          background: "#1f3d5c",
                          borderRadius: 4,
                          color: "#58a6ff",
                          fontSize: 10,
                          fontWeight: 600,
                          marginLeft: 4,
                          padding: "1px 6px",
                        }}
                      >
                        You
                      </span>
                    </span>
                  ) : (
                    `Rank ${entry.rank}`
                  )}
                </td>
                <td
                  style={{
                    color: entry.score !== null ? "#3fb950" : "#6e7681",
                    fontWeight: 600,
                    padding: "8px 12px",
                    textAlign: "right",
                  }}
                >
                  {entry.score !== null ? `${entry.score} pts` : "—"}
                </td>
                <td
                  style={{
                    color: "#c9d1d9",
                    padding: "8px 12px",
                    textAlign: "right",
                  }}
                >
                  {entry.wns !== null && entry.wns !== undefined
                    ? entry.wns.toFixed(4)
                    : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function AssignmentView({ assignment, currentUserId }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>("instructions");

  return (
    <div
      style={{
        background: "#0d1117",
        border: "1px solid #30363d",
        borderRadius: 8,
        padding: 24,
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ color: "#f0f6fc", fontSize: 20, fontWeight: 700, margin: 0 }}>
          {assignment.title}
        </h2>
        {assignment.due_at && (
          <div style={{ color: "#8b949e", fontSize: 13, marginTop: 4 }}>
            Due: {new Date(assignment.due_at).toLocaleString()}
          </div>
        )}
        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <span
            style={{
              background: "#1f2d3d",
              border: "1px solid #30363d",
              borderRadius: 4,
              color: "#8b949e",
              fontSize: 12,
              padding: "2px 8px",
            }}
          >
            {assignment.pdk}
          </span>
          <span
            style={{
              background: "#1f2d3d",
              border: "1px solid #30363d",
              borderRadius: 4,
              color: "#8b949e",
              fontSize: 12,
              padding: "2px 8px",
            }}
          >
            Target: {assignment.target_stage}
          </span>
        </div>
      </div>

      <TabBar active={activeTab} onChange={setActiveTab} />

      {activeTab === "instructions" && (
        <InstructionsTab assignment={assignment} />
      )}

      {activeTab === "submit" && (
        <SubmitTab assignment={assignment} currentUserId={currentUserId} />
      )}

      {activeTab === "leaderboard" && (
        <LeaderboardTab assignment={assignment} currentUserId={currentUserId} />
      )}
    </div>
  );
}
