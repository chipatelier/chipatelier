import React, { useState } from "react";
import { submitJob } from "../../api/jobs";
import { ProjectResponse } from "../../api/projects";

const STAGES = [
  { value: "synth",     label: "Synthesis" },
  { value: "floorplan", label: "Floorplan" },
  { value: "place",     label: "Placement" },
  { value: "cts",       label: "CTS" },
  { value: "route",     label: "Route" },
  { value: "finish",    label: "GDS (Full Flow)" },
];

interface OverrideFields {
  CLOCK_PERIOD: string;
  CORE_UTILIZATION: string;
  PLACE_DENSITY: string;
  TNS_END_PERCENT: string;
}

const OVERRIDE_FIELD_DEFS: { key: keyof OverrideFields; label: string; validate: (v: string) => boolean }[] = [
  { key: "CLOCK_PERIOD",      label: "CLOCK_PERIOD",      validate: (v) => parseFloat(v) > 0 },
  { key: "CORE_UTILIZATION",  label: "CORE_UTILIZATION",  validate: (v) => { const n = parseInt(v); return n >= 1 && n <= 99; } },
  { key: "PLACE_DENSITY",     label: "PLACE_DENSITY",     validate: (v) => { const n = parseFloat(v); return n >= 0.01 && n <= 0.99; } },
  { key: "TNS_END_PERCENT",   label: "TNS_END_PERCENT",   validate: (v) => { const n = parseInt(v); return n >= 0 && n <= 100; } },
];

interface Props {
  project: ProjectResponse;
  hasActiveRun: boolean;
  onSubmitted: (runId: string) => void;
}

export default function NewRunModal({ project, hasActiveRun, onSubmitted }: Props): React.ReactElement {
  const [open, setOpen] = useState(false);
  const [stage, setStage] = useState("route");
  const [overrides, setOverrides] = useState<OverrideFields>({ CLOCK_PERIOD: "", CORE_UTILIZATION: "", PLACE_DENSITY: "", TNS_END_PERCENT: "" });
  const [showOverrides, setShowOverrides] = useState(false);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canOpen = project.verilog_version > 0 && project.config_version > 0 && !hasActiveRun;

  const overrideInvalid = OVERRIDE_FIELD_DEFS.some(({ key, validate }) => {
    const v = overrides[key];
    return v !== "" && !validate(v);
  });

  function getDisabledTitle(): string {
    if (project.verilog_version === 0) return "Upload a Verilog file before submitting a run";
    if (project.config_version === 0) return "Save a config.mk before submitting a run";
    if (hasActiveRun) return "Cancel the active run before starting a new one";
    return "";
  }

  async function handleSubmit(): Promise<void> {
    setSubmitting(true);
    setError(null);
    try {
      const configOverrides: Record<string, string> = {};
      for (const { key } of OVERRIDE_FIELD_DEFS) {
        if (overrides[key] !== "") configOverrides[key] = overrides[key];
      }
      const resp = await submitJob({
        project_id: project.id,
        target_stage: stage,
        source_path: project.latest_source_path ?? undefined,
        config_overrides: Object.keys(configOverrides).length > 0 ? configOverrides : undefined,
        notes: notes || undefined,
      });
      setOpen(false);
      setNotes("");
      setOverrides({ CLOCK_PERIOD: "", CORE_UTILIZATION: "", PLACE_DENSITY: "", TNS_END_PERCENT: "" });
      onSubmitted(resp.run_id);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to submit run");
    } finally {
      setSubmitting(false);
    }
  }

  const S: Record<string, React.CSSProperties> = {
    triggerBtn: { padding: "6px 14px", background: canOpen ? "#238636" : "#21262d", color: canOpen ? "#fff" : "#6e7681", border: `1px solid ${canOpen ? "transparent" : "#30363d"}`, borderRadius: 6, cursor: canOpen ? "pointer" : "not-allowed", fontSize: 13, fontWeight: 600 },
    overlay: { position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center" },
    modal: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 24, width: 480, maxWidth: "90vw" },
    label: { display: "block", fontSize: 11, color: "#8b949e", textTransform: "uppercase" as const, letterSpacing: "0.5px", marginBottom: 4 },
    input: { width: "100%", padding: "6px 8px", background: "#0d1117", border: "1px solid #30363d", borderRadius: 4, color: "#c9d1d9", fontSize: 13, boxSizing: "border-box" as const },
    select: { width: "100%", padding: "6px 8px", background: "#0d1117", border: "1px solid #30363d", borderRadius: 4, color: "#c9d1d9", fontSize: 13 },
  };

  return (
    <>
      <button
        onClick={() => canOpen && setOpen(true)}
        disabled={!canOpen}
        title={getDisabledTitle()}
        style={S.triggerBtn}
        aria-label="New Run"
      >
        New Run
      </button>

      {open && (
        <div style={S.overlay} onClick={() => setOpen(false)}>
          <div style={S.modal} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ margin: "0 0 16px 0", fontSize: 16, color: "#f0f6fc" }}>Submit New Run</h3>

            {error && <div style={{ padding: 8, background: "#3d1f1f", border: "1px solid #da3633", borderRadius: 4, color: "#f85149", fontSize: 12, marginBottom: 12 }}>{error}</div>}

            <div style={{ marginBottom: 12 }}>
              <label style={S.label}>Target Stage</label>
              <select value={stage} onChange={(e) => setStage(e.target.value)} style={S.select}>
                {STAGES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </div>

            <div style={{ border: "1px solid #30363d", borderRadius: 6, marginBottom: 12, overflow: "hidden" }}>
              <button
                type="button"
                onClick={() => setShowOverrides(!showOverrides)}
                style={{ width: "100%", padding: "8px 12px", background: "#1c2128", border: "none", color: "#8b949e", fontSize: 12, textAlign: "left" as const, cursor: "pointer" }}
              >
                {showOverrides ? "▼" : "▶"} Override Parameters <span style={{ color: "#6e7681" }}>(optional)</span>
              </button>
              {showOverrides && (
                <div style={{ padding: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  {OVERRIDE_FIELD_DEFS.map(({ key, label, validate }) => {
                    const v = overrides[key];
                    const invalid = v !== "" && !validate(v);
                    return (
                      <div key={key}>
                        <label style={S.label}>{label}</label>
                        <input
                          style={{ ...S.input, borderColor: invalid ? "#da3633" : "#30363d" }}
                          placeholder="from config.mk"
                          value={v}
                          onChange={(e) => setOverrides((prev) => ({ ...prev, [key]: e.target.value }))}
                        />
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={S.label}>Run Notes (optional)</label>
              <input
                style={S.input}
                placeholder="e.g. testing lower utilization"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>

            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={() => setOpen(false)} style={{ padding: "6px 14px", background: "transparent", color: "#8b949e", border: "1px solid #30363d", borderRadius: 6, cursor: "pointer", fontSize: 13 }}>
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting || overrideInvalid}
                style={{ padding: "6px 16px", background: submitting || overrideInvalid ? "#21262d" : "#238636", color: submitting || overrideInvalid ? "#6e7681" : "#fff", border: "none", borderRadius: 6, cursor: submitting || overrideInvalid ? "not-allowed" : "pointer", fontSize: 13, fontWeight: 600 }}
                aria-label="Submit Run"
              >
                {submitting ? "Submitting…" : "Submit Run"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
