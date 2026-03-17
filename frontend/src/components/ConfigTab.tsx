import React, { useState } from "react";
import { COPY_FEEDBACK_MS } from "../constants";

interface Props {
  config: Record<string, unknown> | null | undefined;
}

export function ConfigTab({ config }: Props): React.ReactElement {
  const [copyDone, setCopyDone] = useState(false);

  function handleCopy(): void {
    const text = config ? JSON.stringify(config, null, 2) : "";
    navigator.clipboard.writeText(text).then(() => {
      setCopyDone(true);
      setTimeout(() => setCopyDone(false), COPY_FEEDBACK_MS);
    });
  }

  return (
    <div style={{ padding: 24, overflowY: "auto" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <h3 style={{ color: "#f0f6fc", fontSize: 15, margin: 0 }}>Config Snapshot</h3>
        {config && (
          <button
            onClick={handleCopy}
            style={{
              padding: "4px 10px",
              background: copyDone ? "#1f4022" : "#21262d",
              color: copyDone ? "#3fb950" : "#8b949e",
              border: "1px solid #30363d",
              borderRadius: 6,
              cursor: "pointer",
              fontSize: 12,
              fontWeight: 500,
            }}
          >
            {copyDone ? "Copied!" : "Copy"}
          </button>
        )}
      </div>
      {config != null ? (
        <pre
          style={{
            background: "#161b22",
            border: "1px solid #30363d",
            borderRadius: 6,
            padding: 16,
            fontSize: 12,
            fontFamily: "monospace",
            color: "#c9d1d9",
            overflow: "auto",
            maxHeight: "60vh",
            margin: 0,
          }}
        >
          {JSON.stringify(config, null, 2)}
        </pre>
      ) : (
        <p style={{ color: "#8b949e", fontSize: 13 }}>
          No config snapshot available for this run.
        </p>
      )}
    </div>
  );
}
