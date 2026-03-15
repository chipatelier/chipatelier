/**
 * InspectSidebar — shows cell instance details from a layout click query.
 *
 * Renders null when no query has been made (elements === null, not loading).
 * Shows "No element at this location" when query returns an empty list.
 * Persists until the user clicks the X dismiss button.
 */
import type { InspectElement } from "../../api/query";

interface InspectSidebarProps {
  /** Queried elements; null means no query has been made yet */
  elements: InspectElement[] | null;
  isLoading: boolean;
  onDismiss: () => void;
}

export function InspectSidebar({
  elements,
  isLoading,
  onDismiss,
}: InspectSidebarProps) {
  // Hidden when no query has been initiated
  if (elements === null && !isLoading) return null;

  return (
    <div
      style={{
        width: 320,
        borderLeft: "1px solid #30363d",
        background: "#0d1117",
        display: "flex",
        flexDirection: "column",
        height: "100%",
        flexShrink: 0,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 12px",
          borderBottom: "1px solid #30363d",
        }}
      >
        <span
          style={{
            fontWeight: 600,
            fontSize: 13,
            color: "#e6edf3",
          }}
        >
          Layout Inspector
        </span>
        <button
          onClick={onDismiss}
          aria-label="Close inspector"
          style={{
            background: "none",
            border: "none",
            color: "#8b949e",
            cursor: "pointer",
            fontSize: 16,
            lineHeight: 1,
            padding: 2,
          }}
        >
          ✕
        </button>
      </div>

      {/* Content */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: 12,
        }}
      >
        {isLoading && (
          <p style={{ fontSize: 13, color: "#8b949e" }}>Querying...</p>
        )}

        {!isLoading && elements !== null && elements.length === 0 && (
          <p style={{ fontSize: 13, color: "#8b949e" }}>
            No element at this location
          </p>
        )}

        {!isLoading &&
          elements !== null &&
          elements.map((el, i) => (
            <div
              key={i}
              style={{
                marginBottom: 12,
                padding: 10,
                background: "#161b22",
                borderRadius: 6,
                border: "1px solid #30363d",
              }}
            >
              <p
                style={{
                  fontFamily: "monospace",
                  fontSize: 13,
                  fontWeight: 700,
                  color: "#e6edf3",
                  margin: 0,
                }}
              >
                {el.name}
              </p>
              {el.master && (
                <p
                  style={{
                    fontSize: 12,
                    color: "#8b949e",
                    margin: "4px 0 0",
                  }}
                >
                  Type: {el.master}
                </p>
              )}
              {el.nets.length > 0 && (
                <div style={{ marginTop: 6 }}>
                  <p
                    style={{
                      fontSize: 11,
                      color: "#6e7681",
                      margin: "0 0 4px",
                      textTransform: "uppercase",
                      letterSpacing: "0.04em",
                    }}
                  >
                    Nets
                  </p>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {el.nets.map((net) => (
                      <span
                        key={net}
                        style={{
                          fontSize: 11,
                          background: "#1f3a5f",
                          color: "#79c0ff",
                          padding: "2px 6px",
                          borderRadius: 4,
                          fontFamily: "monospace",
                        }}
                      >
                        {net}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
      </div>
    </div>
  );
}
