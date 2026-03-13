/**
 * RunHistoryTable — displays a project's runs with status, stages, and PPA columns.
 *
 * RSLT-04: Table columns: Status, Target Stage, Stage Completed, Created At, WNS, DRC.
 * Rows are clickable — navigates to run detail page.
 * Sorted by created_at DESC (API order is preserved).
 */
import React from "react";
import { useNavigate } from "react-router-dom";
import type { RunSummary } from "../../api/projects";

interface Props {
  runs: RunSummary[];
  projectId: string;
}

type StatusColor = { bg: string; text: string };

const STATUS_COLORS: Record<string, StatusColor> = {
  queued:    { bg: "#1f3a5f", text: "#58a6ff" },
  starting:  { bg: "#1f3a5f", text: "#58a6ff" },
  running:   { bg: "#1f3a5f", text: "#58a6ff" },
  complete:  { bg: "#1f4022", text: "#3fb950" },
  failed:    { bg: "#3d1f1f", text: "#f85149" },
  timeout:   { bg: "#3d1f1f", text: "#f85149" },
  cancelled: { bg: "#2d2a1f", text: "#d29922" },
};

function StatusBadge({ status }: { status: string }): React.ReactElement {
  const style = STATUS_COLORS[status] ?? { bg: "#30363d", text: "#8b949e" };
  return (
    <span
      style={{
        padding: "2px 8px",
        borderRadius: 12,
        fontSize: 11,
        fontWeight: 600,
        background: style.bg,
        color: style.text,
        textTransform: "uppercase",
        letterSpacing: "0.05em",
        whiteSpace: "nowrap",
      }}
    >
      {status}
    </span>
  );
}

function WnsCell({ wns }: { wns: number | null }): React.ReactElement {
  if (wns === null) {
    return <span style={{ color: "#6e7681" }}>—</span>;
  }
  const color = wns >= -0.1 ? "#3fb950" : wns >= -0.5 ? "#d29922" : "#f85149";
  return <span style={{ color, fontWeight: 500 }}>{wns.toFixed(3)}</span>;
}

function DrcCell({ drc }: { drc: number | null }): React.ReactElement {
  if (drc === null) {
    return <span style={{ color: "#6e7681" }}>—</span>;
  }
  const color = drc === 0 ? "#3fb950" : "#f85149";
  return <span style={{ color, fontWeight: 500 }}>{drc}</span>;
}

export function RunHistoryTable({ runs, projectId }: Props): React.ReactElement {
  const navigate = useNavigate();

  if (runs.length === 0) {
    return (
      <p style={{ color: "#8b949e", fontSize: 13 }}>
        No runs yet. Upload your design files then click "New Run".
      </p>
    );
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: 13,
        }}
      >
        <thead>
          <tr style={{ borderBottom: "1px solid #30363d", color: "#8b949e", textAlign: "left" }}>
            <th style={{ padding: "8px 12px", fontWeight: 600 }}>Status</th>
            <th style={{ padding: "8px 12px", fontWeight: 600 }}>Target Stage</th>
            <th style={{ padding: "8px 12px", fontWeight: 600 }}>Stage Completed</th>
            <th style={{ padding: "8px 12px", fontWeight: 600 }}>Created At</th>
            <th style={{ padding: "8px 12px", fontWeight: 600 }}>WNS (ns)</th>
            <th style={{ padding: "8px 12px", fontWeight: 600 }}>DRC</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr
              key={run.id}
              onClick={() => navigate(`/projects/${projectId}/runs/${run.id}`)}
              style={{
                borderBottom: "1px solid #21262d",
                cursor: "pointer",
                transition: "background 0.1s",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLTableRowElement).style.background = "#161b22";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLTableRowElement).style.background = "transparent";
              }}
            >
              <td style={{ padding: "10px 12px" }}>
                <StatusBadge status={run.status} />
              </td>
              <td style={{ padding: "10px 12px", color: "#c9d1d9" }}>
                {run.target_stage ?? "—"}
              </td>
              <td style={{ padding: "10px 12px", color: "#c9d1d9" }}>
                {run.stage_completed ?? "—"}
              </td>
              <td style={{ padding: "10px 12px", color: "#8b949e" }}>
                {new Date(run.created_at).toLocaleString()}
              </td>
              <td style={{ padding: "10px 12px" }}>
                <WnsCell wns={run.ppa?.worst_negative_slack != null ? Number(run.ppa.worst_negative_slack) : null} />
              </td>
              <td style={{ padding: "10px 12px" }}>
                <DrcCell drc={run.ppa?.drc_violations != null ? Number(run.ppa.drc_violations) : null} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
