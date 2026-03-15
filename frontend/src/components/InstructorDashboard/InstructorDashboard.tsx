/**
 * InstructorDashboard — per-student progress table with CSV export.
 *
 * Shows: student name, run count, last run status, submission status, score.
 * Columns are sortable (click header). CSV export button triggers download.
 * Queue info (queued/running jobs) shown at top.
 */
import { useState, useEffect } from "react";
import {
  getDashboard,
  getDashboardExportUrl,
  DashboardResponse,
  StudentProgress,
} from "../../api/courses";

interface Props {
  courseId: string;
}

type SortKey = keyof StudentProgress;
type SortDir = "asc" | "desc";

// ---------------------------------------------------------------------------
// Sort helper
// ---------------------------------------------------------------------------

function sortStudents(
  students: StudentProgress[],
  key: SortKey,
  dir: SortDir
): StudentProgress[] {
  return [...students].sort((a, b) => {
    const aVal = a[key] ?? "";
    const bVal = b[key] ?? "";
    if (aVal < bVal) return dir === "asc" ? -1 : 1;
    if (aVal > bVal) return dir === "asc" ? 1 : -1;
    return 0;
  });
}

// ---------------------------------------------------------------------------
// Column header button
// ---------------------------------------------------------------------------

function SortableHeader({
  label,
  sortKey,
  currentKey,
  currentDir,
  onSort,
}: {
  label: string;
  sortKey: SortKey;
  currentKey: SortKey;
  currentDir: SortDir;
  onSort: (key: SortKey) => void;
}) {
  const isActive = currentKey === sortKey;
  return (
    <th
      onClick={() => onSort(sortKey)}
      style={{
        background: "#161b22",
        borderBottom: "1px solid #30363d",
        color: isActive ? "#f0f6fc" : "#8b949e",
        cursor: "pointer",
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "0.04em",
        padding: "8px 12px",
        textAlign: "left",
        textTransform: "uppercase",
        userSelect: "none",
        whiteSpace: "nowrap",
      }}
    >
      {label}
      {isActive && (
        <span style={{ marginLeft: 4, fontSize: 10 }}>
          {currentDir === "asc" ? "▲" : "▼"}
        </span>
      )}
    </th>
  );
}

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string | null }) {
  if (!status) {
    return <span style={{ color: "#6e7681", fontSize: 12 }}>—</span>;
  }
  const colorMap: Record<string, { bg: string; text: string }> = {
    complete: { bg: "#1a3d1a", text: "#3fb950" },
    running: { bg: "#1f2d3d", text: "#58a6ff" },
    failed: { bg: "#3d1f1f", text: "#f85149" },
    queued: { bg: "#2d2a1a", text: "#e3b341" },
    submitted: { bg: "#1a3d1a", text: "#3fb950" },
    not_submitted: { bg: "#1c2128", text: "#6e7681" },
  };
  const colors = colorMap[status] ?? { bg: "#1c2128", text: "#8b949e" };
  return (
    <span
      style={{
        background: colors.bg,
        borderRadius: 4,
        color: colors.text,
        fontSize: 11,
        fontWeight: 600,
        padding: "2px 8px",
      }}
    >
      {status}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function InstructorDashboard({ courseId }: Props) {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("display_name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  useEffect(() => {
    getDashboard(courseId)
      .then(setData)
      .catch((err: unknown) => {
        const e = err as { response?: { data?: { detail?: string } }; message?: string };
        setError(e.response?.data?.detail ?? e.message ?? "Failed to load dashboard");
      })
      .finally(() => setLoading(false));
  }, [courseId]);

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  if (loading) {
    return (
      <div style={{ color: "#8b949e", fontSize: 14, padding: 24 }}>
        Loading dashboard...
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          background: "#3d1f1f",
          border: "1px solid #6e4040",
          borderRadius: 8,
          color: "#f85149",
          fontSize: 14,
          padding: 16,
        }}
      >
        {error}
      </div>
    );
  }

  if (!data) return null;

  const sortedStudents = sortStudents(data.students, sortKey, sortDir);

  return (
    <div
      style={{
        background: "#0d1117",
        border: "1px solid #30363d",
        borderRadius: 8,
        overflow: "hidden",
      }}
    >
      {/* Queue info + export */}
      <div
        style={{
          alignItems: "center",
          background: "#161b22",
          borderBottom: "1px solid #30363d",
          display: "flex",
          gap: 16,
          justifyContent: "space-between",
          padding: "12px 16px",
        }}
      >
        <div style={{ color: "#8b949e", fontSize: 13 }}>
          Jobs waiting:{" "}
          <strong style={{ color: "#f0f6fc" }}>{data.queue_info.queued}</strong>
          {" | "}Running:{" "}
          <strong style={{ color: "#f0f6fc" }}>{data.queue_info.running}</strong>
        </div>
        <a
          href={getDashboardExportUrl(courseId)}
          download
          style={{
            background: "#21262d",
            border: "1px solid #30363d",
            borderRadius: 6,
            color: "#c9d1d9",
            cursor: "pointer",
            fontSize: 13,
            fontWeight: 600,
            padding: "6px 12px",
            textDecoration: "none",
          }}
        >
          Export CSV
        </a>
      </div>

      {/* Student progress table */}
      {data.students.length === 0 ? (
        <div
          style={{
            color: "#6e7681",
            fontStyle: "italic",
            fontSize: 14,
            padding: 24,
            textAlign: "center",
          }}
        >
          No students enrolled yet.
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <SortableHeader
                  label="Student"
                  sortKey="display_name"
                  currentKey={sortKey}
                  currentDir={sortDir}
                  onSort={handleSort}
                />
                <SortableHeader
                  label="Runs"
                  sortKey="run_count"
                  currentKey={sortKey}
                  currentDir={sortDir}
                  onSort={handleSort}
                />
                <SortableHeader
                  label="Last Run"
                  sortKey="last_run_status"
                  currentKey={sortKey}
                  currentDir={sortDir}
                  onSort={handleSort}
                />
                <SortableHeader
                  label="Submission"
                  sortKey="submission_status"
                  currentKey={sortKey}
                  currentDir={sortDir}
                  onSort={handleSort}
                />
                <SortableHeader
                  label="Score"
                  sortKey="score"
                  currentKey={sortKey}
                  currentDir={sortDir}
                  onSort={handleSort}
                />
              </tr>
            </thead>
            <tbody>
              {sortedStudents.map((student, i) => (
                <tr
                  key={student.user_id}
                  style={{
                    background: i % 2 === 0 ? "#0d1117" : "#161b22",
                    borderTop: "1px solid #1c2128",
                  }}
                >
                  <td
                    style={{
                      color: "#c9d1d9",
                      fontSize: 13,
                      fontWeight: 500,
                      padding: "10px 12px",
                    }}
                  >
                    {student.display_name}
                  </td>
                  <td
                    style={{
                      color: "#8b949e",
                      fontSize: 13,
                      padding: "10px 12px",
                      textAlign: "center",
                    }}
                  >
                    {student.run_count}
                  </td>
                  <td style={{ padding: "10px 12px" }}>
                    <StatusBadge status={student.last_run_status} />
                  </td>
                  <td style={{ padding: "10px 12px" }}>
                    <StatusBadge status={student.submission_status} />
                  </td>
                  <td
                    style={{
                      color: student.score !== null ? "#3fb950" : "#6e7681",
                      fontSize: 13,
                      fontWeight: 600,
                      padding: "10px 12px",
                      textAlign: "center",
                    }}
                  >
                    {student.score !== null ? `${student.score} pts` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
