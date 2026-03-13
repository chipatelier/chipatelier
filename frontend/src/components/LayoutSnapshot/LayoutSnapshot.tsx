/**
 * LayoutSnapshot — displays the static layout PNG with VNC launcher and download links.
 *
 * LOCKED DESIGN (from CONTEXT.md must_haves):
 *   - Layout PNG image fills width
 *   - "Open in VNC viewer" button directly below the PNG
 *   - Download links section below VNC button (GDS, DEF, Timing Report)
 *
 * The PNG fast-path is PERMANENT per CLAUDE.md — this component must always
 * render the PNG preview. Phase 2's tiled viewer is additive, not a replacement.
 */
import React from "react";
import type { ArtifactURLs } from "../../api/artifacts";

interface Props {
  runId: string;
  artifacts: ArtifactURLs | null;
  /** Called when user clicks "Open in VNC viewer" — plan 01-06 implements the session start */
  onOpenVnc?: (runId: string) => void;
}

function DownloadLink({ href, label }: { href: string | null; label: string }): React.ReactElement | null {
  if (!href) return null;
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "6px 12px",
        background: "#21262d",
        border: "1px solid #30363d",
        borderRadius: 6,
        color: "#58a6ff",
        fontSize: 13,
        textDecoration: "none",
        fontWeight: 500,
      }}
    >
      {label}
    </a>
  );
}

export function LayoutSnapshot({ runId, artifacts, onOpenVnc }: Props): React.ReactElement {
  const pngUrl = artifacts?.layout_png_url ?? null;
  const hasPng = Boolean(pngUrl);
  const hasArtifacts = Boolean(artifacts);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Layout PNG */}
      <div
        style={{
          background: "#0d1117",
          border: "1px solid #30363d",
          borderRadius: 8,
          overflow: "hidden",
          minHeight: 200,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {!hasArtifacts ? (
          <div style={{ color: "#8b949e", fontSize: 14, padding: 24, textAlign: "center" }}>
            <div
              style={{
                width: 24,
                height: 24,
                border: "2px solid #30363d",
                borderTopColor: "#58a6ff",
                borderRadius: "50%",
                margin: "0 auto 12px",
                animation: "spin 1s linear infinite",
              }}
            />
            Loading layout preview...
          </div>
        ) : !hasPng ? (
          <div style={{ color: "#8b949e", fontSize: 14, padding: 24, textAlign: "center" }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>&#9203;</div>
            Layout preview generating...
            <div style={{ fontSize: 12, marginTop: 4, color: "#6e7681" }}>
              The layout PNG is being rendered. Refresh in a few seconds.
            </div>
          </div>
        ) : (
          <img
            src={pngUrl!}
            alt="Layout snapshot"
            style={{ width: "100%", display: "block", borderRadius: 8 }}
          />
        )}
      </div>

      {/* Open in VNC viewer button — LOCKED position: directly below PNG */}
      <button
        onClick={() => onOpenVnc?.(runId)}
        style={{
          padding: "8px 16px",
          background: "#1f6feb",
          color: "#fff",
          border: "none",
          borderRadius: 6,
          cursor: "pointer",
          fontSize: 13,
          fontWeight: 600,
          alignSelf: "flex-start",
        }}
      >
        Open in VNC Viewer
      </button>

      {/* Download links — below VNC button */}
      {hasArtifacts && (
        <div>
          <div style={{ fontSize: 12, color: "#8b949e", marginBottom: 8, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Downloads
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <DownloadLink href={artifacts?.gds_url ?? null} label="Download GDS" />
            <DownloadLink href={artifacts?.def_url ?? null} label="Download DEF" />
            <DownloadLink href={artifacts?.timing_report_url ?? null} label="Download Timing Report" />
          </div>
          {!artifacts?.gds_url && !artifacts?.def_url && (
            <div style={{ fontSize: 12, color: "#6e7681", marginTop: 8 }}>
              Download links will appear once artifacts are ready.
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
