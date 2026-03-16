/**
 * PpaMetricCards — displays WNS, TNS, DRC, Core Area, Total Power as color-coded cards.
 *
 * Color thresholds (from PLAN must_haves):
 *   WNS: green >= -0.1ns, yellow >= -0.5ns, red < -0.5ns or null
 *   TNS: green >= -1.0ns, yellow >= -5.0ns, red worse
 *   DRC: green == 0, red > 0
 *   Area/Power: neutral (informational only)
 *
 * Phase 3 additions:
 *   - Optional runId prop enables AI explain links on WNS and DRC cards
 *   - AiExplainPanel renders below the grid when an explain type is active
 */
import React, { useState } from "react";
import { AiExplainPanel } from "../AiExplainPanel";

export interface PpaMetrics {
  worst_negative_slack: number | null;
  total_negative_slack: number | null;
  drc_violations: number | null;
  core_area: number | null;
  total_power: number | null;
  flow_complete?: boolean;
}

interface Props {
  metrics: PpaMetrics | null;
  runId?: string;
}

type ColorStatus = "green" | "yellow" | "red" | "neutral";

function getWnsColor(wns: number | null): ColorStatus {
  if (wns === null) return "red";
  if (wns >= -0.1) return "green";
  if (wns >= -0.5) return "yellow";
  return "red";
}

function getTnsColor(tns: number | null): ColorStatus {
  if (tns === null) return "red";
  if (tns >= -1.0) return "green";
  if (tns >= -5.0) return "yellow";
  return "red";
}

function getDrcColor(drc: number | null): ColorStatus {
  if (drc === null) return "neutral";
  if (drc === 0) return "green";
  return "red";
}

const COLOR_STYLES: Record<ColorStatus, { dot: string; border: string }> = {
  green:   { dot: "#3fb950", border: "#1f4022" },
  yellow:  { dot: "#d29922", border: "#2d2a1f" },
  red:     { dot: "#f85149", border: "#3d1f1f" },
  neutral: { dot: "#6e7681", border: "#30363d" },
};

interface CardProps {
  label: string;
  value: string;
  color: ColorStatus;
  unit?: string;
  onExplain?: () => void;
}

function MetricCard({ label, value, color, unit, onExplain }: CardProps): React.ReactElement {
  const style = COLOR_STYLES[color];
  return (
    <div
      style={{
        background: "#161b22",
        border: `1px solid ${style.border}`,
        borderRadius: 8,
        padding: "16px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: style.dot,
            flexShrink: 0,
          }}
        />
        <span style={{ fontSize: 12, color: "#8b949e", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em" }}>
          {label}
        </span>
      </div>
      <div style={{ fontSize: 22, fontWeight: 700, color: value === "—" ? "#6e7681" : "#f0f6fc" }}>
        {value}
        {unit && value !== "—" && (
          <span style={{ fontSize: 13, fontWeight: 400, color: "#8b949e", marginLeft: 4 }}>{unit}</span>
        )}
      </div>
      {onExplain && (
        <button
          onClick={onExplain}
          style={{
            fontSize: 11,
            color: "#8b5cf6",
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: 0,
            marginTop: 4,
            textAlign: "left",
          }}
          aria-label={`Get AI explanation for ${label}`}
        >
          Explain ◆
        </button>
      )}
    </div>
  );
}

export function PpaMetricCards({ metrics, runId }: Props): React.ReactElement {
  const [activeExplain, setActiveExplain] = useState<"timing" | "drc" | null>(null);

  const formatNs = (v: number | null): string =>
    v !== null ? v.toFixed(3) : "—";

  const formatArea = (v: number | null): string =>
    v !== null ? v.toFixed(1) : "—";

  const formatPower = (v: number | null): string =>
    v !== null ? (v * 1000).toFixed(3) : "—";

  const formatDrc = (v: number | null): string =>
    v !== null ? String(v) : "—";

  return (
    <div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 16,
        }}
      >
        <MetricCard
          label="WNS"
          value={formatNs(metrics?.worst_negative_slack ?? null)}
          color={getWnsColor(metrics?.worst_negative_slack ?? null)}
          unit="ns"
          onExplain={runId ? () => setActiveExplain(activeExplain === "timing" ? null : "timing") : undefined}
        />
        <MetricCard
          label="TNS"
          value={formatNs(metrics?.total_negative_slack ?? null)}
          color={getTnsColor(metrics?.total_negative_slack ?? null)}
          unit="ns"
        />
        <MetricCard
          label="DRC Violations"
          value={formatDrc(metrics?.drc_violations ?? null)}
          color={getDrcColor(metrics?.drc_violations ?? null)}
          onExplain={runId ? () => setActiveExplain(activeExplain === "drc" ? null : "drc") : undefined}
        />
        <MetricCard
          label="Core Area"
          value={formatArea(metrics?.core_area ?? null)}
          color="neutral"
          unit="µm²"
        />
        <MetricCard
          label="Total Power"
          value={formatPower(metrics?.total_power ?? null)}
          color="neutral"
          unit="mW"
        />
      </div>

      {/* AI explain panel — rendered below grid when active */}
      {activeExplain && runId && (
        <AiExplainPanel runId={runId} explainType={activeExplain} />
      )}
    </div>
  );
}
