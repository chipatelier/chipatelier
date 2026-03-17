import React from "react";
import { CURATED_PARAMS } from "./ParamMetadata";

interface ParamFormProps {
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
  lockedParams: Record<string, string>;
  editableParams: string[]; // empty = all curated params editable
}

const FORM: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 16,
  padding: 16,
};

const ROW: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 4,
};

const ROW_HEADER: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 8,
};

const LABEL: React.CSSProperties = {
  fontWeight: 500,
  fontSize: 13,
  color: "#e6edf3",
};

const LOCKED_BADGE: React.CSSProperties = {
  fontSize: 11,
  background: "#2d2a1a",
  color: "#e3b341",
  padding: "2px 8px",
  borderRadius: 4,
};

const INPUT_ROW: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 8,
};

function inputStyle(locked: boolean): React.CSSProperties {
  return {
    border: "1px solid #30363d",
    borderRadius: 6,
    padding: "4px 8px",
    width: 128,
    background: locked ? "#21262d" : "#0d1117",
    color: locked ? "#6e7681" : "#e6edf3",
    cursor: locked ? "not-allowed" : "text",
    fontSize: 13,
    outline: "none",
  };
}

const UNIT: React.CSSProperties = {
  fontSize: 11,
  color: "#8b949e",
};

const RANGE: React.CSSProperties = {
  fontSize: 11,
  color: "#6e7681",
};

const DESC: React.CSSProperties = {
  fontSize: 11,
  color: "#8b949e",
};

export function ParamForm({
  values,
  onChange,
  lockedParams,
  editableParams,
}: ParamFormProps) {
  const visibleParams =
    editableParams.length > 0
      ? CURATED_PARAMS.filter(
          (p) => editableParams.includes(p.key) || p.key in lockedParams
        )
      : CURATED_PARAMS;

  return (
    <div style={FORM}>
      {visibleParams.map((param) => {
        const isLocked = param.key in lockedParams;
        const value = isLocked
          ? lockedParams[param.key]
          : (values[param.key] ?? "");
        return (
          <div key={param.key} style={ROW}>
            <div style={ROW_HEADER}>
              <label
                htmlFor={`param-${param.key}`}
                style={LABEL}
              >
                {param.label}
              </label>
              {isLocked && (
                <span style={LOCKED_BADGE}>
                  Locked by instructor
                </span>
              )}
            </div>
            <div style={INPUT_ROW}>
              <input
                id={`param-${param.key}`}
                type="number"
                min={param.min}
                max={param.max}
                step="any"
                value={value}
                disabled={isLocked}
                onChange={(e) =>
                  !isLocked && onChange(param.key, e.target.value)
                }
                style={inputStyle(isLocked)}
                aria-label={param.label}
              />
              {param.unit && (
                <span style={UNIT}>{param.unit}</span>
              )}
              <span style={RANGE}>
                {param.min}–{param.max}
              </span>
            </div>
            <p style={DESC}>{param.description}</p>
          </div>
        );
      })}
    </div>
  );
}
