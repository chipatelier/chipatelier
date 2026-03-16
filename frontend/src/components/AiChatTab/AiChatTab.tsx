/**
 * AiChatTab — multi-turn AI chat panel for the Run Detail page.
 *
 * Features:
 *   - Collapsible context summary (stage, status, WNS, DRC, log count, model)
 *   - Scrollable message list with user/assistant bubbles
 *   - Streaming cursor (blinking █) during token delivery
 *   - Chat history cleared when runId changes
 *   - Last 10 turns (20 messages) sent per request
 *   - Error banner on Ollama 503 or stream interruption
 *
 * Privacy: context summary shows only stage/status/metrics — never student PII or paths.
 */
import React, { useEffect, useRef, useState } from "react";
import { useStore } from "../../store";
import { streamChat, ChatMessage } from "../../api/ai";
import { RunStatusResponse } from "../../api/jobs";

interface AiChatTabProps {
  runId: string;
  run?: RunStatusResponse | null;
}

// Blinking cursor keyframes injected once
const CURSOR_STYLE = `
@keyframes chipCursorBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
`;

export function AiChatTab({ runId, run }: AiChatTabProps): React.ReactElement {
  const chatHistory = useStore((s) => s.chatHistory);
  const chatStreaming = useStore((s) => s.chatStreaming);
  const setChatHistory = useStore((s) => s.setChatHistory);
  const appendChatToken = useStore((s) => s.appendChatToken);
  const setChatStreaming = useStore((s) => s.setChatStreaming);
  const clearChat = useStore((s) => s.clearChat);
  const accessToken = useStore((s) => s.accessToken);

  const [input, setInput] = useState("");
  const [isContextExpanded, setIsContextExpanded] = useState(true);
  const [streamError, setStreamError] = useState<string | null>(null);

  const messageListRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Clear chat history when navigating to a different run
  useEffect(() => {
    clearChat();
    setStreamError(null);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  // Auto-scroll to bottom as tokens arrive
  useEffect(() => {
    const el = messageListRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [chatHistory]);

  // Auto-resize textarea (min 1 row, max 3 rows)
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    const lineH = 22; // approx line height at 14px
    const maxH = lineH * 3 + 16; // 3 rows + padding
    ta.style.height = Math.min(ta.scrollHeight, maxH) + "px";
  }, [input]);

  async function handleSend(): Promise<void> {
    const trimmed = input.trim();
    if (!trimmed || chatStreaming) return;
    if (!accessToken) return;

    // Add user message
    const userMsg: ChatMessage = { role: "user", content: trimmed };
    const newHistory: ChatMessage[] = [...chatHistory, userMsg];
    setChatHistory(newHistory);
    setInput("");
    setStreamError(null);
    setChatStreaming(true);

    try {
      // Send last 10 turns (20 messages) of history before this user message
      const historyToSend = chatHistory.slice(-20);
      const gen = streamChat(runId, trimmed, historyToSend, accessToken);

      for await (const chunk of gen) {
        if (chunk.error) {
          setStreamError(chunk.error);
          setChatStreaming(false);
          return;
        }
        if (chunk.done) {
          setChatStreaming(false);
          return;
        }
        if (chunk.token) {
          appendChatToken(chunk.token);
        }
      }
    } catch {
      setStreamError("[Response interrupted — please try again]");
    } finally {
      setChatStreaming(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>): void {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  // Context summary values
  const stage = run?.stage_completed ?? "not started";
  const status = run?.status ?? "unknown";
  const ppa = (run?.ppa as Record<string, unknown> | null | undefined) ?? {};
  const wns = ppa["worst_negative_slack"] != null
    ? String(ppa["worst_negative_slack"]) + " ns"
    : "—";
  const drc = ppa["drc_routing_errors"] != null
    ? String(ppa["drc_routing_errors"]) + " violations"
    : "—";

  const isSendDisabled = chatStreaming || input.trim().length === 0;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: "#0d1117",
        overflow: "hidden",
      }}
    >
      {/* Inject cursor blink keyframes */}
      <style>{CURSOR_STYLE}</style>

      {/* Context summary panel */}
      <div
        role="note"
        aria-label="AI context summary"
        aria-expanded={isContextExpanded}
        onClick={() => setIsContextExpanded((v) => !v)}
        style={{
          background: "#1e1433",
          borderBottom: "1px solid #2d1f4a",
          padding: "10px 16px",
          cursor: "pointer",
          flexShrink: 0,
          userSelect: "none",
        }}
      >
        <span style={{ fontSize: 12, color: "#8b5cf6", fontWeight: 600 }}>
          {isContextExpanded ? "▾" : "▸"} Context:
        </span>
        {isContextExpanded ? (
          <div style={{ marginTop: 4 }}>
            <span style={{ fontSize: 13, color: "#8b949e", marginRight: 12 }}>
              Stage <strong style={{ color: "#c9d1d9" }}>{stage}</strong>
            </span>
            <span style={{ fontSize: 13, color: "#8b949e", marginRight: 12 }}>
              Status <strong style={{ color: "#c9d1d9" }}>{status}</strong>
            </span>
            <span style={{ fontSize: 13, color: "#8b949e", marginRight: 12 }}>
              WNS <strong style={{ color: "#c9d1d9" }}>{wns}</strong>
            </span>
            <span style={{ fontSize: 13, color: "#8b949e", marginRight: 12 }}>
              DRC <strong style={{ color: "#c9d1d9" }}>{drc}</strong>
            </span>
            <span style={{ fontSize: 13, color: "#8b949e", marginRight: 12 }}>
              50 log lines sent
            </span>
            <span style={{ fontSize: 11, color: "#6e7681" }}>
              deepseek-r1:7b · runs locally
            </span>
          </div>
        ) : (
          <span style={{ fontSize: 13, color: "#8b949e", marginLeft: 8 }}>
            {stage} · {status} · WNS {wns} · DRC {drc}
          </span>
        )}
      </div>

      {/* Message list */}
      <div
        ref={messageListRef}
        role="log"
        aria-live="polite"
        aria-label="AI chat messages"
        style={{
          flex: 1,
          overflowY: "auto",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 16,
          minHeight: 0,
        }}
      >
        {chatHistory.length === 0 && !chatStreaming && (
          <div
            style={{
              textAlign: "center",
              color: "#6e7681",
              fontSize: 14,
              marginTop: 40,
            }}
          >
            Ask anything about your run.
          </div>
        )}

        {chatHistory.map((msg, idx) => {
          const isLast = idx === chatHistory.length - 1;
          const isStreaming = chatStreaming && isLast && msg.role === "assistant";

          if (msg.role === "user") {
            return (
              <div
                key={idx}
                role="article"
                aria-label={`You said: ${msg.content}`}
                style={{ display: "flex", flexDirection: "column", alignItems: "flex-end" }}
              >
                <div
                  style={{
                    fontSize: 11,
                    color: "#6e7681",
                    textAlign: "right",
                    marginBottom: 4,
                  }}
                >
                  You
                </div>
                <div
                  style={{
                    marginLeft: "auto",
                    maxWidth: "70%",
                    background: "#1c2128",
                    border: "1px solid #30363d",
                    borderRadius: "12px 12px 2px 12px",
                    padding: "10px 14px",
                    fontSize: 14,
                    color: "#c9d1d9",
                    lineHeight: 1.5,
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {msg.content}
                </div>
              </div>
            );
          }

          // Assistant message
          return (
            <div
              key={idx}
              role="article"
              aria-label={`AI response: ${msg.content}`}
              style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}
            >
              <div
                style={{
                  fontSize: 11,
                  color: "#8b5cf6",
                  fontWeight: 600,
                  marginBottom: 4,
                }}
              >
                AI
              </div>
              <div
                style={{
                  marginRight: "auto",
                  maxWidth: "85%",
                  background: "#161b22",
                  border: "1px solid #30363d",
                  borderRadius: "2px 12px 12px 12px",
                  padding: "10px 14px",
                  fontSize: 14,
                  color: "#c9d1d9",
                  lineHeight: 1.6,
                  whiteSpace: "pre-wrap",
                }}
              >
                {msg.content}
                {isStreaming && (
                  <span
                    aria-hidden="true"
                    style={{
                      color: "#8b5cf6",
                      animation: "chipCursorBlink 1s step-end infinite",
                    }}
                  >
                    █
                  </span>
                )}
                {!isStreaming && isLast && msg.role === "assistant" && (
                  <span
                    aria-live="assertive"
                    style={{
                      position: "absolute",
                      width: 1,
                      height: 1,
                      overflow: "hidden",
                      clip: "rect(0,0,0,0)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    AI response complete
                  </span>
                )}
              </div>
            </div>
          );
        })}

        {/* Stream error display */}
        {streamError && (
          <div
            style={{
              fontSize: 13,
              fontStyle: "italic",
              color: "#f85149",
              padding: "8px 14px",
              background: "#3d1f1f",
              border: "1px solid #da3633",
              borderRadius: 6,
              maxWidth: "85%",
            }}
          >
            {streamError}
          </div>
        )}
      </div>

      {/* Input bar */}
      <div
        style={{
          background: "#161b22",
          borderTop: "1px solid #30363d",
          padding: "12px 16px",
          display: "flex",
          gap: 8,
          alignItems: "flex-end",
          flexShrink: 0,
        }}
      >
        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your run..."
          aria-label="Chat message"
          disabled={false}
          style={{
            flex: 1,
            background: "#0d1117",
            border: "1px solid #30363d",
            borderRadius: 6,
            padding: "8px 12px",
            color: "#c9d1d9",
            fontSize: 14,
            resize: "none",
            outline: "none",
            fontFamily: "sans-serif",
            lineHeight: 1.5,
            minHeight: 38,
            maxHeight: 82,
            overflowY: "auto",
          }}
        />
        <button
          onClick={handleSend}
          disabled={isSendDisabled}
          aria-label="Send message"
          aria-disabled={isSendDisabled}
          style={{
            padding: "8px 16px",
            background: isSendDisabled ? "#21262d" : "#1f6feb",
            color: isSendDisabled ? "#6e7681" : "#fff",
            border: "none",
            borderRadius: 6,
            fontSize: 13,
            fontWeight: 600,
            cursor: isSendDisabled ? "not-allowed" : "pointer",
            flexShrink: 0,
            alignSelf: "flex-end",
            height: 38,
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}
