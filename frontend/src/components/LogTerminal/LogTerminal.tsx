/**
 * LogTerminal — xterm.js terminal for ORFS log streaming.
 *
 * Locked behaviors (from CONTEXT.md):
 *   - scrollback: 50000 (not 0/unlimited — prevents OOM on long ORFS runs)
 *   - Auto-scroll enabled by default
 *   - Pause auto-scroll when user scrolls up (detected via term.onScroll)
 *   - "Jump to bottom" button appears when auto-scroll is paused
 *   - Auto-scroll resumes when user scrolls back to bottom
 *   - Stage separator lines (starting with "═══") rendered in cyan (\x1b[36m)
 */
import { useEffect, useRef, useState } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { useLogStream } from "../../hooks/useLogStream";
import "@xterm/xterm/css/xterm.css";

interface LogTerminalProps {
  runId: string | null;
  /** If false, suppress auto-reconnect (e.g., for completed runs). */
  isRunning?: boolean;
}

export function LogTerminal({ runId, isRunning = true }: LogTerminalProps): React.ReactElement {
  const termRef = useRef<HTMLDivElement>(null);
  const termInstance = useRef<Terminal | null>(null);
  const autoScrollRef = useRef(true);
  const [showJumpBtn, setShowJumpBtn] = useState(false);

  // Initialize terminal once on mount
  useEffect(() => {
    const term = new Terminal({
      scrollback: 50000,
      convertEol: true,
      theme: {
        background: "#0d1117",
        foreground: "#c9d1d9",
        cursor: "#c9d1d9",
        selectionBackground: "#264f78",
      },
      fontSize: 13,
      fontFamily: "Menlo, Monaco, 'Courier New', monospace",
      cursorBlink: false,
    });

    const fit = new FitAddon();
    term.loadAddon(fit);

    if (termRef.current) {
      term.open(termRef.current);
      fit.fit();
    }

    // Auto-scroll state machine:
    // Detect when user scrolls up (disable auto-scroll, show jump button)
    // and when they scroll back to bottom (re-enable auto-scroll)
    term.onScroll(() => {
      const viewport = term.buffer.active.viewportY;
      const totalLines = term.buffer.active.length;
      const atBottom = viewport >= totalLines - term.rows;
      autoScrollRef.current = atBottom;
      setShowJumpBtn(!atBottom);
    });

    termInstance.current = term;

    // Resize observer to keep terminal fitted to container
    const observer = new ResizeObserver(() => {
      try {
        fit.fit();
      } catch {
        // Ignore if terminal is disposed
      }
    });
    if (termRef.current) {
      observer.observe(termRef.current);
    }

    return () => {
      observer.disconnect();
      term.dispose();
      termInstance.current = null;
    };
  }, []);

  // Handle incoming log lines
  const handleLine = (line: string): void => {
    const term = termInstance.current;
    if (!term) return;

    // Stage separator lines: render in cyan for visual distinction
    if (line.startsWith("═══")) {
      term.writeln(`\x1b[36m${line}\x1b[0m`);
    } else {
      term.writeln(line);
    }

    // Scroll to bottom if auto-scroll is active
    if (autoScrollRef.current) {
      term.scrollToBottom();
    }
  };

  useLogStream(runId, handleLine, { reconnect: isRunning });

  const handleJumpToBottom = (): void => {
    termInstance.current?.scrollToBottom();
    autoScrollRef.current = true;
    setShowJumpBtn(false);
  };

  return (
    <div
      style={{
        position: "relative",
        height: "100%",
        width: "100%",
        background: "#0d1117",
        overflow: "hidden",
      }}
    >
      <div ref={termRef} style={{ height: "100%", width: "100%" }} />
      {showJumpBtn && (
        <button
          onClick={handleJumpToBottom}
          style={{
            position: "absolute",
            bottom: 16,
            right: 16,
            padding: "6px 12px",
            background: "#1f6feb",
            color: "#ffffff",
            border: "none",
            borderRadius: 4,
            cursor: "pointer",
            fontSize: 12,
            fontFamily: "sans-serif",
            zIndex: 10,
            boxShadow: "0 2px 8px rgba(0,0,0,0.4)",
          }}
        >
          Jump to bottom
        </button>
      )}
    </div>
  );
}
