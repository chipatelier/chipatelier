import React, { useEffect, useRef, useState } from "react";
import Editor from "@monaco-editor/react";
import { ProjectResponse, getProjectSource, getProjectConfig, updateProject, uploadFiles } from "../../api/projects";

interface Props {
  project: ProjectResponse;
  onProjectUpdate: (updated: ProjectResponse) => void;
}

export default function FileConfigTab({ project, onProjectUpdate }: Props): React.ReactElement {
  const [verilogContent, setVerilogContent] = useState<string | null>(null);
  const [verilogFilename, setVerilogFilename] = useState<string | null>(null);
  const [verilogError, setVerilogError] = useState(false);
  const [configContent, setConfigContent] = useState("");
  const [configDirty, setConfigDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getProjectSource(project.id)
      .then((r) => { setVerilogContent(r.content); setVerilogFilename(r.filename); })
      .catch(() => setVerilogError(true));

    getProjectConfig(project.id)
      .then((r) => setConfigContent(r.content));
  }, [project.id]);

  async function handleUpload(files: FileList | null): Promise<void> {
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      await uploadFiles(project.id, Array.from(files));
      // Refetch project to get updated verilog_version and latest_source_path
      const { getProject } = await import("../../api/projects");
      const updated = await getProject(project.id);
      onProjectUpdate(updated);
      // Reload verilog content
      const src = await getProjectSource(project.id);
      setVerilogContent(src.content);
      setVerilogFilename(src.filename);
      setVerilogError(false);
    } catch {
      setSaveError("Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleSaveConfig(): Promise<void> {
    setSaving(true);
    setSaveError(null);
    try {
      const updated = await updateProject(project.id, { config_mk: configContent });
      onProjectUpdate(updated);
      setConfigDirty(false);
    } catch {
      setSaveError("Failed to save config.mk");
    } finally {
      setSaving(false);
    }
  }

  const panelStyle: React.CSSProperties = { flex: 1, minWidth: 0, background: "#161b22", border: "1px solid #30363d", borderRadius: 8, overflow: "hidden", display: "flex", flexDirection: "column" };
  const panelHeader: React.CSSProperties = { padding: "10px 14px", borderBottom: "1px solid #30363d", display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 13, color: "#f0f6fc", fontWeight: 600, background: "#1c2128" };

  return (
    <div style={{ display: "flex", gap: 16, height: "calc(100vh - 200px)", padding: 24 }}>
      {/* Verilog Panel */}
      <div style={panelStyle}>
        <div style={panelHeader}>
          <span>{verilogFilename ?? "Verilog Source"}{project.verilog_version > 0 ? ` · v${project.verilog_version}` : ""}</span>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".v,.sv"
              style={{ display: "none" }}
              onChange={(e) => handleUpload(e.target.files)}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              style={{ padding: "4px 10px", background: "#1f6feb", color: "#fff", border: "none", borderRadius: 4, cursor: uploading ? "not-allowed" : "pointer", fontSize: 12 }}
            >
              {uploading ? "Uploading…" : project.verilog_version === 0 ? "Upload Verilog" : "Replace"}
            </button>
          </div>
        </div>
        <div style={{ flex: 1 }}>
          {verilogError ? (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "#8b949e", fontSize: 13 }}>
              No Verilog uploaded yet
            </div>
          ) : (
            <Editor
              height="100%"
              language="systemverilog"
              value={verilogContent ?? ""}
              theme="vs-dark"
              options={{ readOnly: true, minimap: { enabled: false }, fontSize: 12 }}
            />
          )}
        </div>
      </div>

      {/* Config Panel */}
      <div style={panelStyle}>
        <div style={panelHeader}>
          <span>
            config.mk{project.config_version > 0 ? ` · v${project.config_version}` : ""}
            {configDirty && <span style={{ color: "#f0883e", marginLeft: 8, fontWeight: 400 }}>● Unsaved</span>}
          </span>
          <button
            onClick={handleSaveConfig}
            disabled={saving || !configDirty}
            style={{ padding: "4px 10px", background: saving || !configDirty ? "#21262d" : "#238636", color: saving || !configDirty ? "#6e7681" : "#fff", border: "none", borderRadius: 4, cursor: saving || !configDirty ? "not-allowed" : "pointer", fontSize: 12 }}
            aria-label="Save"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
        {saveError && <div style={{ padding: "6px 14px", fontSize: 12, color: "#f85149", background: "#3d1f1f" }}>{saveError}</div>}
        <div style={{ flex: 1 }}>
          <Editor
            height="100%"
            language="makefile"
            value={configContent}
            theme="vs-dark"
            options={{ minimap: { enabled: false }, fontSize: 12 }}
            onChange={(v) => { setConfigContent(v ?? ""); setConfigDirty(true); }}
          />
        </div>
      </div>
    </div>
  );
}
