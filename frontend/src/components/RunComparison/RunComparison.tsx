/**
 * RunComparison — side-by-side metrics + config diff table for up to 4 runs.
 *
 * Props:
 *   runs: Array of run objects with ppa (PPA metrics) and config (config.mk snapshot).
 *
 * Features:
 *   - Metrics section: WNS, TNS, DRC violations, core utilization, total power
 *   - Color coding per metric row: best=green, worst=red, middle=yellow
 *   - Config differences section: shows only params that differ across selected runs
 */

export interface CompareRun {
  id: string;
  created_at: string;
  ppa: Record<string, number | null | undefined>;
  config: Record<string, string | null | undefined>;
}

interface Props {
  runs: CompareRun[];
}

// ---------------------------------------------------------------------------
// Metrics definition
// ---------------------------------------------------------------------------

const METRICS: Array<{ key: string; label: string; higherBetter: boolean }> = [
  { key: "worst_negative_slack", label: "WNS (ns)", higherBetter: true },
  { key: "total_negative_slack", label: "TNS (ns)", higherBetter: true },
  { key: "drc_violations", label: "DRC Violations", higherBetter: false },
  { key: "core_utilization", label: "Core Utilization (%)", higherBetter: false },
  { key: "total_power", label: "Total Power (W)", higherBetter: false },
];

// ---------------------------------------------------------------------------
// Color coding helper
// ---------------------------------------------------------------------------

function colorClass(
  value: number,
  values: number[],
  higherBetter: boolean
): string {
  if (values.length === 0) return "";
  const sorted = [...values].sort((a, b) =>
    higherBetter ? b - a : a - b
  );
  if (value === sorted[0]) return "bg-green-100 text-green-800";
  if (value === sorted[sorted.length - 1]) return "bg-red-100 text-red-800";
  return "bg-yellow-50 text-yellow-800";
}

// Inline style equivalents for environments without Tailwind
function colorStyle(
  value: number,
  values: number[],
  higherBetter: boolean
): { background: string; color: string } {
  if (values.length === 0) return { background: "transparent", color: "#c9d1d9" };
  const sorted = [...values].sort((a, b) =>
    higherBetter ? b - a : a - b
  );
  if (value === sorted[0])
    return { background: "#1a3d1a", color: "#3fb950" };
  if (value === sorted[sorted.length - 1])
    return { background: "#3d1f1f", color: "#f85149" };
  return { background: "#2d2a1a", color: "#e3b341" };
}

// ---------------------------------------------------------------------------
// Config diff helper
// ---------------------------------------------------------------------------

function getConfigDiffs(
  runs: CompareRun[]
): Array<{ key: string; values: Array<string | null | undefined> }> {
  if (runs.length < 2) return [];
  const allKeys = Array.from(
    new Set(runs.flatMap((r) => Object.keys(r.config || {})))
  ).sort();
  return allKeys
    .map((key) => ({
      key,
      values: runs.map((r) => r.config?.[key]),
    }))
    .filter(({ values }) => {
      const first = values[0];
      return values.some((v) => v !== first);
    });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function RunComparison({ runs }: Props) {
  if (runs.length < 2) {
    return (
      <div
        style={{
          color: "#6e7681",
          fontSize: 14,
          padding: "24px",
          textAlign: "center",
          border: "1px dashed #30363d",
          borderRadius: 8,
        }}
      >
        Select 2 to 4 runs from your run history to compare metrics side by side.
      </div>
    );
  }

  const configDiffs = getConfigDiffs(runs);

  // Column header style
  const headerStyle: React.CSSProperties = {
    background: "#161b22",
    borderBottom: "1px solid #30363d",
    color: "#8b949e",
    fontSize: 11,
    fontWeight: 600,
    padding: "8px 12px",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
    textAlign: "center" as const,
    minWidth: 100,
  };

  const metricLabelStyle: React.CSSProperties = {
    background: "#0d1117",
    borderRight: "1px solid #30363d",
    color: "#8b949e",
    fontSize: 13,
    padding: "8px 12px",
    minWidth: 160,
    whiteSpace: "nowrap",
  };

  const cellStyle: React.CSSProperties = {
    fontSize: 13,
    fontWeight: 600,
    padding: "8px 12px",
    textAlign: "center",
    borderRight: "1px solid #1c2128",
  };

  return (
    <div
      style={{
        background: "#0d1117",
        border: "1px solid #30363d",
        borderRadius: 8,
        overflow: "hidden",
      }}
    >
      {/* Metrics table */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ ...headerStyle, textAlign: "left" }}>Metric</th>
              {runs.map((run, i) => (
                <th key={run.id} style={headerStyle}>
                  Run {i + 1}
                  <div
                    style={{ fontSize: 10, color: "#6e7681", fontWeight: 400, marginTop: 2 }}
                  >
                    {new Date(run.created_at).toLocaleDateString()}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {METRICS.map((metric, rowIdx) => {
              const values = runs
                .map((r) => r.ppa?.[metric.key])
                .filter((v): v is number => v !== null && v !== undefined);

              return (
                <tr
                  key={metric.key}
                  style={{
                    borderTop: "1px solid #1c2128",
                    background: rowIdx % 2 === 0 ? "#0d1117" : "#161b22",
                  }}
                >
                  <td style={metricLabelStyle}>{metric.label}</td>
                  {runs.map((run) => {
                    const val = run.ppa?.[metric.key];
                    const hasValue = val !== null && val !== undefined;
                    const style = hasValue
                      ? {
                          ...cellStyle,
                          ...colorStyle(val as number, values, metric.higherBetter),
                        }
                      : { ...cellStyle, color: "#6e7681" };
                    // Combine color class for test targeting (Tailwind-like className)
                    const cssClass = hasValue
                      ? colorClass(val as number, values, metric.higherBetter)
                      : "";

                    return (
                      <td
                        key={run.id}
                        style={style}
                        className={cssClass}
                        data-metric={metric.key}
                      >
                        {hasValue
                          ? typeof val === "number"
                            ? val.toFixed(4)
                            : val
                          : "—"}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Config differences section */}
      {configDiffs.length > 0 && (
        <div>
          <div
            style={{
              borderTop: "1px solid #30363d",
              color: "#8b949e",
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: "0.04em",
              padding: "10px 12px 6px",
              textTransform: "uppercase",
              background: "#161b22",
            }}
          >
            Config Differences
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <tbody>
              {configDiffs.map(({ key, values }, rowIdx) => (
                <tr
                  key={key}
                  style={{
                    borderTop: "1px solid #1c2128",
                    background: rowIdx % 2 === 0 ? "#0d1117" : "#161b22",
                  }}
                >
                  <td style={metricLabelStyle}>{key}</td>
                  {values.map((val, i) => (
                    <td
                      key={i}
                      style={{ ...cellStyle, color: "#c9d1d9", background: "transparent" }}
                      data-config-key={key}
                    >
                      {val ?? "—"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
