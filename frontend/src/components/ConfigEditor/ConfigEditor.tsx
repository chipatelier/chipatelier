import { useState } from "react";
import Editor from "@monaco-editor/react";
import { ParamForm } from "./ParamForm";
import { AiAdvisorPanel } from "../AiAdvisorPanel";

interface ConfigEditorProps {
  configContent: string;
  onChange: (newContent: string) => void;
  lockedParams?: Record<string, string>;
  editableParams?: string[];
  /** Optional run ID for AI advisor context. When present, advisor has PPA metrics. */
  runId?: string | null;
}

function parseParamValues(content: string): Record<string, string> {
  // Extract "export KEY = VALUE" lines from config.mk
  const values: Record<string, string> = {};
  for (const line of content.split("\n")) {
    const m = line.match(/^export\s+(\w+)\s*=\s*(.+)/);
    if (m) values[m[1]] = m[2].trim();
  }
  return values;
}

function applyParamChange(
  content: string,
  key: string,
  value: string
): string {
  const regex = new RegExp(`^(export\\s+${key}\\s*=\\s*)(.+)`, "m");
  if (regex.test(content)) {
    return content.replace(regex, `$1${value}`);
  }
  return content + `\nexport ${key} = ${value}`;
}

export function ConfigEditor({
  configContent,
  onChange,
  lockedParams = {},
  editableParams = [],
  runId = null,
}: ConfigEditorProps) {
  const [mode, setMode] = useState<"form" | "raw">("form");
  const [showAdvisor, setShowAdvisor] = useState(false);
  const paramValues = parseParamValues(configContent);

  const handleParamChange = (key: string, value: string) => {
    onChange(applyParamChange(configContent, key, value));
  };

  return (
    <div className="config-editor flex flex-col h-full">
      <div className="config-editor-header flex gap-2 p-2 border-b" style={{ alignItems: "center" }}>
        <button
          onClick={() => setMode("form")}
          className={`px-3 py-1 rounded text-sm font-medium ${
            mode === "form"
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-700"
          }`}
          aria-pressed={mode === "form"}
        >
          Form
        </button>
        <button
          onClick={() => setMode("raw")}
          className={`px-3 py-1 rounded text-sm font-medium ${
            mode === "raw"
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-700"
          }`}
          aria-pressed={mode === "raw"}
        >
          Raw
        </button>
        <button
          onClick={() => setShowAdvisor(!showAdvisor)}
          style={{
            marginLeft: "auto",
            padding: "6px 14px",
            fontSize: 12,
            fontWeight: 600,
            background: "#1e1433",
            color: "#8b5cf6",
            border: "1px solid #2d1f4a",
            borderRadius: 6,
            cursor: "pointer",
          }}
          aria-pressed={showAdvisor}
        >
          Get AI Suggestions ◆
        </button>
      </div>
      {mode === "form" ? (
        <ParamForm
          values={paramValues}
          onChange={handleParamChange}
          lockedParams={lockedParams}
          editableParams={editableParams}
        />
      ) : (
        <Editor
          height="500px"
          defaultLanguage="makefile"
          value={configContent}
          onChange={(v) => onChange(v ?? "")}
          theme="vs-dark"
          options={{ minimap: { enabled: false } }}
        />
      )}
      {showAdvisor && (
        <div style={{ padding: "0 16px 16px 16px" }}>
          <AiAdvisorPanel runId={runId ?? null} configContent={configContent} />
        </div>
      )}
    </div>
  );
}

export default ConfigEditor;
