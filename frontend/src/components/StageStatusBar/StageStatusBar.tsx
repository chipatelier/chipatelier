/**
 * StageStatusBar — always-visible ORFS pipeline progress indicator.
 *
 * Locked design (from CONTEXT.md):
 *   Synth  Floor  Place  CTS  Route  GDS
 *   done→"✓" (green), running→"↻" (blue, spinning), pending→"-" (grey)
 *
 * Always rendered above the run detail tabs, regardless of tab selection.
 */
import React from "react";
import { Stage, StageState, STAGES } from "../../store/jobSlice";

interface StageStatusBarProps {
  stageProgress: Record<Stage, StageState>;
}

const STAGE_LABELS: Record<Stage, string> = {
  synthesis: "Synth",
  floorplan: "Floor",
  place: "Place",
  cts: "CTS",
  route: "Route",
  gds: "GDS",
};

const STATE_COLORS: Record<StageState, string> = {
  done: "#3fb950",    // green
  running: "#1f6feb", // blue
  pending: "#6e7681", // grey
};

const STATE_ICONS: Record<StageState, string> = {
  done: "✓",
  running: "↻",
  pending: "-",
};

interface StageItemProps {
  label: string;
  state: StageState;
  isLast: boolean;
}

function StageItem({ label, state, isLast }: StageItemProps): React.ReactElement {
  const color = STATE_COLORS[state];
  const icon = STATE_ICONS[state];
  const isRunning = state === "running";

  return (
    <>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 2,
          minWidth: 52,
        }}
      >
        <span
          style={{
            color,
            fontSize: 16,
            fontWeight: isRunning ? 700 : 400,
            lineHeight: 1,
            // Spinning animation for running state via CSS animation
            display: "inline-block",
            animation: isRunning ? "spin 1s linear infinite" : "none",
          }}
          title={state}
        >
          {icon}
        </span>
        <span
          style={{
            fontSize: 11,
            color,
            fontFamily: "sans-serif",
            fontWeight: state === "done" ? 600 : 400,
            letterSpacing: "0.02em",
          }}
        >
          {label}
        </span>
      </div>
      {!isLast && (
        <div
          style={{
            height: 1,
            width: 20,
            background: "#30363d",
            alignSelf: "center",
            marginBottom: 16,
            flexShrink: 0,
          }}
        />
      )}
    </>
  );
}

export function StageStatusBar({ stageProgress }: StageStatusBarProps): React.ReactElement {
  return (
    <>
      {/* Spinning animation keyframes injected once */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 0,
          padding: "8px 16px",
          background: "#161b22",
          borderBottom: "1px solid #30363d",
          flexShrink: 0,
        }}
        role="status"
        aria-label="ORFS pipeline stage progress"
      >
        {STAGES.map((stage, idx) => (
          <StageItem
            key={stage}
            label={STAGE_LABELS[stage]}
            state={stageProgress[stage]}
            isLast={idx === STAGES.length - 1}
          />
        ))}
      </div>
    </>
  );
}
