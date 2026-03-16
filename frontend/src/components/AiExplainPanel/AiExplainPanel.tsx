/**
 * AiExplainPanel — shared panel for log/timing/drc AI explanations.
 *
 * Behavior:
 *   - Reads from explain cache (key = "${runId}:${explainType}")
 *   - Cache hit: renders immediately with no API call
 *   - Cache miss: calls the appropriate explain API on mount
 *   - 503 errors → user-facing "unavailable" banner
 *   - Other errors → connection error banner
 *   - Collapsible header with ▲/▼ toggle
 *   - Privacy footer: "Analyzed by deepseek-r1:7b · Runs locally on this server"
 *   - All styles inline — no Tailwind, no CSS modules
 */
import { useState, useEffect } from "react";
import { useStore } from "../../store";
import { explainLog, explainTiming, explainDrc } from "../../api/ai";

export type ExplainType = "log" | "timing" | "drc";

interface AiExplainPanelProps {
  runId: string;
  explainType: ExplainType;
}

const SPINNER_KEYFRAMES = `
@keyframes ai-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
`;

function SpinnerIcon(): React.ReactElement {
  return (
    <>
      <style>{SPINNER_KEYFRAMES}</style>
      <svg
        width="16"
        height="16"
        viewBox="0 0 16 16"
        fill="none"
        style={{ animation: "ai-spin 1s linear infinite", flexShrink: 0 }}
        aria-hidden="true"
      >
        <circle cx="8" cy="8" r="6" stroke="#8b5cf6" strokeWidth="2" strokeDasharray="28" strokeDashoffset="10" />
      </svg>
    </>
  );
}

export function AiExplainPanel({ runId, explainType }: AiExplainPanelProps): React.ReactElement {
  const explainCache = useStore((s) => s.explainCache);
  const setExplainCache = useStore((s) => s.setExplainCache);

  const cacheKey = `${runId}:${explainType}`;
  const cached = explainCache[cacheKey] ?? null;

  const [loading, setLoading] = useState(!cached);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    if (cached) return;

    let cancelled = false;

    async function fetchExplanation(): Promise<void> {
      setLoading(true);
      setError(null);
      try {
        let resp;
        if (explainType === "log") {
          resp = await explainLog(runId);
        } else if (explainType === "timing") {
          resp = await explainTiming(runId);
        } else {
          resp = await explainDrc(runId);
        }
        if (!cancelled) {
          setExplainCache(cacheKey, resp.explanation);
        }
      } catch (err: unknown) {
        if (cancelled) return;
        // Check for 503 (Ollama unavailable)
        const status = (err as { response?: { status?: number } })?.response?.status;
        if (status === 503) {
          setError(
            "AI assistant is currently unavailable. Contact your instructor if this persists."
          );
        } else {
          setError("Failed to reach AI service. Check your connection and try again.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchExplanation();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, explainType]);

  const explanation = cached;

  return (
    <div
      role="region"
      aria-label="AI explanation panel"
      style={{
        border: "1px solid #2d1f4a",
        borderRadius: 6,
        overflow: "hidden",
        marginTop: 8,
      }}
    >
      {/* Header */}
      <div
        style={{
          background: "#1e1433",
          borderBottom: collapsed ? "none" : "1px solid #2d1f4a",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "6px 12px",
        }}
      >
        <span
          style={{
            fontSize: 12,
            color: "#8b5cf6",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
          }}
        >
          ◆ AI Explanation
        </span>
        <button
          onClick={() => setCollapsed((c) => !c)}
          style={{
            background: "none",
            border: "none",
            color: "#6e7681",
            fontSize: 12,
            cursor: "pointer",
            padding: "0 4px",
          }}
          aria-label={collapsed ? "Expand AI explanation" : "Collapse AI explanation"}
        >
          {collapsed ? "▼" : "▲"}
        </button>
      </div>

      {/* Body */}
      {!collapsed && (
        <div
          style={{
            background: "#0d1117",
            maxHeight: 400,
            overflowY: "auto",
            padding: "12px 14px",
          }}
        >
          {loading && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                color: "#8b949e",
                fontSize: 13,
              }}
            >
              <SpinnerIcon />
              Generating explanation...
            </div>
          )}

          {!loading && error && (
            <div
              style={{
                background: "#3d1f1f",
                border: "1px solid #da3633",
                borderRadius: 4,
                padding: "10px 12px",
                color: "#f85149",
                fontSize: 13,
              }}
              role="alert"
            >
              {error}
            </div>
          )}

          {!loading && !error && explanation && (
            <p
              style={{
                fontSize: 14,
                color: "#c9d1d9",
                lineHeight: 1.6,
                margin: 0,
                whiteSpace: "pre-wrap",
              }}
            >
              {explanation}
            </p>
          )}

          {/* Privacy footer */}
          {!loading && !error && explanation && (
            <div
              style={{
                marginTop: 12,
                paddingTop: 8,
                borderTop: "1px solid #21262d",
                fontSize: 11,
                color: "#6e7681",
              }}
            >
              Analyzed by deepseek-r1:7b · Runs locally on this server
            </div>
          )}
        </div>
      )}
    </div>
  );
}
