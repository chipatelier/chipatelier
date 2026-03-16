/**
 * AiAdvisorPanel — config parameter suggestion panel.
 *
 * Behavior:
 *   - "Get AI Suggestions ◆" button triggers advisorConfig API call
 *   - Parses suggestions text into per-parameter cards
 *   - Format: "PARAM_NAME: current -> suggested | Reason: explanation"
 *   - Falls back to raw text display if parsing fails
 *   - No-run-context banner when runId is null
 *   - 503 → "unavailable" banner; other errors → connection error banner
 *   - Privacy footer: "Analyzed by deepseek-r1:7b · Runs locally on this server"
 *   - All styles inline — no Tailwind, no CSS modules
 */
import { useState } from "react";
import { useStore } from "../../store";
import { advisorConfig } from "../../api/ai";

interface AiAdvisorPanelProps {
  runId: string | null;
  configContent: string;
}

interface ParsedSuggestion {
  param: string;
  current: string;
  suggested: string;
  reason: string;
}

const SUGGESTION_REGEX =
  /^(\w+):\s*(.+?)\s*->\s*(.+?)\s*\|\s*Reason:\s*(.+)$/gm;

function parseSuggestions(text: string): ParsedSuggestion[] {
  const results: ParsedSuggestion[] = [];
  let match: RegExpExecArray | null;
  SUGGESTION_REGEX.lastIndex = 0;
  while ((match = SUGGESTION_REGEX.exec(text)) !== null) {
    results.push({
      param: match[1],
      current: match[2],
      suggested: match[3],
      reason: match[4],
    });
  }
  return results;
}

const SPINNER_KEYFRAMES = `
@keyframes ai-advisor-spin {
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
        style={{ animation: "ai-advisor-spin 1s linear infinite", flexShrink: 0 }}
        aria-hidden="true"
      >
        <circle cx="8" cy="8" r="6" stroke="#8b5cf6" strokeWidth="2" strokeDasharray="28" strokeDashoffset="10" />
      </svg>
    </>
  );
}

export function AiAdvisorPanel({ runId, configContent: _configContent }: AiAdvisorPanelProps): React.ReactElement {
  const setAdvisorResult = useStore((s) => s.setAdvisorResult);
  const advisorResult = useStore((s) => s.advisorResult);
  const advisorRunId = useStore((s) => s.advisorRunId);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetched, setFetched] = useState(false);

  // Use cached result if it matches the current run
  const currentResult = advisorResult && advisorRunId === runId ? advisorResult : null;

  async function handleGetSuggestions(): Promise<void> {
    if (!runId) return;

    setLoading(true);
    setError(null);
    setFetched(false);

    try {
      const resp = await advisorConfig(runId);
      setAdvisorResult(resp, runId);
      setFetched(true);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 503) {
        setError(
          "AI assistant is currently unavailable. Contact your instructor if this persists."
        );
      } else {
        setError("Failed to reach AI service. Check your connection and try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  const suggestions = currentResult?.suggestions ?? null;
  const parsedCards = suggestions ? parseSuggestions(suggestions) : [];
  const showRaw = suggestions !== null && parsedCards.length === 0;

  return (
    <div
      role="region"
      aria-label="AI config advisor panel"
      style={{
        border: "1px solid #2d1f4a",
        borderRadius: 6,
        overflow: "hidden",
        marginTop: 8,
      }}
    >
      {/* Header with trigger button */}
      <div
        style={{
          background: "#1e1433",
          borderBottom: "1px solid #2d1f4a",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "8px 12px",
          flexWrap: "wrap",
          gap: 8,
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
          ◆ AI Config Advisor
        </span>
        <button
          onClick={handleGetSuggestions}
          disabled={loading || !runId}
          style={{
            padding: "6px 14px",
            fontSize: 12,
            fontWeight: 600,
            background: "#1e1433",
            color: loading || !runId ? "#6e7681" : "#8b5cf6",
            border: `1px solid ${loading || !runId ? "#30363d" : "#2d1f4a"}`,
            borderRadius: 6,
            cursor: loading || !runId ? "not-allowed" : "pointer",
            whiteSpace: "nowrap",
          }}
          aria-label="Get AI config suggestions"
        >
          Get AI Suggestions ◆
        </button>
      </div>

      {/* Body */}
      <div
        style={{
          background: "#0d1117",
          padding: "12px 14px",
        }}
      >
        {/* No run context banner */}
        {!runId && (
          <div
            style={{
              background: "#2d2a1f",
              border: "1px solid #d29922",
              borderRadius: 4,
              padding: "10px 12px",
              color: "#d29922",
              fontSize: 12,
              marginBottom: 8,
            }}
            role="note"
          >
            No run metrics available — suggestions are general. Run your design once for grounded advice.
          </div>
        )}

        {/* Loading */}
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
            Analyzing your config...
          </div>
        )}

        {/* Error */}
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

        {/* Parsed suggestion cards */}
        {!loading && !error && parsedCards.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {parsedCards.map((card) => (
              <div
                key={card.param}
                style={{
                  background: "#0d1117",
                  border: "1px solid #30363d",
                  borderRadius: 6,
                  padding: "12px 14px",
                }}
              >
                <div
                  style={{
                    fontSize: 12,
                    color: "#8b949e",
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.04em",
                    marginBottom: 6,
                  }}
                >
                  {card.param}
                </div>
                <div
                  style={{
                    fontSize: 15,
                    fontWeight: 700,
                    color: "#f0f6fc",
                    marginBottom: 4,
                  }}
                >
                  {card.current}
                  <span style={{ color: "#6e7681", fontWeight: 400 }}> → </span>
                  {card.suggested}
                </div>
                <div
                  style={{
                    fontSize: 13,
                    color: "#c9d1d9",
                    lineHeight: 1.5,
                  }}
                >
                  {card.reason}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Raw fallback */}
        {!loading && !error && showRaw && (
          <p
            style={{
              fontSize: 13,
              color: "#c9d1d9",
              lineHeight: 1.6,
              margin: 0,
              whiteSpace: "pre-wrap",
            }}
          >
            {suggestions}
          </p>
        )}

        {/* Idle state: prompt to click the button */}
        {!loading && !error && !suggestions && !fetched && runId && (
          <p style={{ fontSize: 13, color: "#6e7681", margin: 0 }}>
            Click "Get AI Suggestions" to analyze your current configuration.
          </p>
        )}

        {/* Privacy footer (shown when results are visible) */}
        {!loading && !error && suggestions && (
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
    </div>
  );
}
