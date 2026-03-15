/**
 * CheckpointCards — displays checkpoint criteria pass/fail and scoring.
 *
 * Two modes:
 *   Preview mode (no gradeResult): computes pass/fail client-side from ppa + rules.
 *   Result mode (with gradeResult): shows actual evaluation from the Celery task.
 *
 * Hard gate display: green checkmark if pass, red X if fail.
 * Scored display: "WNS: 40/40 pts" or "20/40 pts (partial credit)" or "0/40 pts (failed)"
 */

interface CheckpointRule {
  metric: string;
  op: string;
  value: number | boolean;
}

interface ScoredRule extends CheckpointRule {
  points: number;
  partial?: { threshold: number; points: number };
}

interface CheckpointRules {
  hard?: CheckpointRule[];
  scored?: ScoredRule[];
}

interface HardResult {
  metric: string;
  passed: boolean;
  actual?: number | boolean | null;
}

interface ScoredResult {
  metric: string;
  awarded: number;
  max_points: number;
  passed: boolean;
  partial_credit: boolean;
  actual?: number | null;
}

interface GradeResult {
  score: number;
  checkpoint_results: {
    hard: HardResult[];
    scored: ScoredResult[];
    hard_gate_blocked: boolean;
  };
}

interface Props {
  checkpointRules: CheckpointRules;
  ppa: Record<string, number | null>;
  gradeResult?: GradeResult;
}

// ---------------------------------------------------------------------------
// Client-side preview computation (mirrors evaluate_checkpoint_rules in Python)
// ---------------------------------------------------------------------------

function compare(actual: number | boolean | null | undefined, op: string, threshold: number | boolean): boolean {
  if (actual === null || actual === undefined) return false;
  if (op === "eq") return actual === threshold;
  if (op === "gte") return (actual as number) >= (threshold as number);
  if (op === "lte") return (actual as number) <= (threshold as number);
  if (op === "gt") return (actual as number) > (threshold as number);
  if (op === "lt") return (actual as number) < (threshold as number);
  return false;
}

function computePreview(ppa: Record<string, number | null>, rules: CheckpointRules): {
  hard: HardResult[];
  scored: ScoredResult[];
  hard_gate_blocked: boolean;
  total_score: number;
} {
  const hardRules = rules.hard ?? [];
  const scoredRules = rules.scored ?? [];

  let hardGatePassed = true;
  const hard: HardResult[] = hardRules.map((rule) => {
    const actual = ppa[rule.metric] ?? null;
    const passed = compare(actual, rule.op, rule.value);
    if (!passed) hardGatePassed = false;
    return { metric: rule.metric, passed, actual };
  });

  let totalScore = 0;
  const scored: ScoredResult[] = scoredRules.map((rule) => {
    const actual = ppa[rule.metric] ?? null;
    const passed = compare(actual, rule.op, rule.value);
    let awarded = 0;
    let partialCredit = false;

    if (passed) {
      awarded = rule.points;
    } else if (rule.partial && actual !== null) {
      if (compare(actual, rule.op, rule.partial.threshold)) {
        awarded = rule.partial.points;
        partialCredit = true;
      }
    }

    if (hardGatePassed) {
      totalScore += awarded;
    }

    return {
      metric: rule.metric,
      awarded,
      max_points: rule.points,
      passed,
      partial_credit: partialCredit,
      actual,
    };
  });

  return {
    hard,
    scored,
    hard_gate_blocked: !hardGatePassed,
    total_score: hardGatePassed ? totalScore : 0,
  };
}

// ---------------------------------------------------------------------------
// Display helpers
// ---------------------------------------------------------------------------

const METRIC_LABELS: Record<string, string> = {
  drc_violations: "DRC Violations",
  worst_negative_slack: "WNS",
  total_negative_slack: "TNS",
  total_power: "Total Power",
  die_area: "Die Area",
  core_utilization: "Core Utilization",
  flow_complete: "Flow Complete",
};

function metricLabel(metric: string): string {
  return METRIC_LABELS[metric] ?? metric;
}

function formatActual(metric: string, actual: number | boolean | null | undefined): string {
  if (actual === null || actual === undefined) return "N/A";
  if (typeof actual === "boolean") return actual ? "true" : "false";
  if (metric.includes("slack")) return `${actual.toFixed(3)} ns`;
  if (metric.includes("power")) return `${(actual * 1000).toFixed(3)} mW`;
  if (metric.includes("area")) return `${actual.toFixed(1)} µm²`;
  return String(actual);
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface HardCardProps {
  result: HardResult;
}

function HardGateCard({ result }: HardCardProps) {
  const borderColor = result.passed ? "#1f4022" : "#3d1f1f";
  const iconColor = result.passed ? "#3fb950" : "#f85149";
  const icon = result.passed ? "✓" : "✗";

  return (
    <div
      style={{
        background: "#161b22",
        border: `1px solid ${borderColor}`,
        borderRadius: 8,
        padding: "12px 16px",
        display: "flex",
        alignItems: "center",
        gap: 12,
      }}
    >
      <span
        style={{
          fontSize: 18,
          fontWeight: 700,
          color: iconColor,
          flexShrink: 0,
        }}
      >
        {icon}
      </span>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 12, color: "#8b949e", fontWeight: 600, textTransform: "uppercase" }}>
          Hard Gate — {metricLabel(result.metric)}
        </div>
        {result.actual !== undefined && result.actual !== null && (
          <div style={{ fontSize: 13, color: "#c9d1d9", marginTop: 2 }}>
            Actual: {formatActual(result.metric, result.actual)}
          </div>
        )}
      </div>
      <span
        style={{
          fontSize: 12,
          color: result.passed ? "#3fb950" : "#f85149",
          fontWeight: 600,
        }}
      >
        {result.passed ? "PASS" : "FAIL"}
      </span>
    </div>
  );
}

interface ScoredCardProps {
  result: ScoredResult;
  blocked: boolean;
}

function ScoredCriterionCard({ result, blocked }: ScoredCardProps) {
  const fullPoints = result.awarded === result.max_points && result.awarded > 0;
  const partialPoints = result.partial_credit && result.awarded > 0;
  const noPoints = result.awarded === 0;

  const borderColor = blocked
    ? "#30363d"
    : fullPoints
    ? "#1f4022"
    : partialPoints
    ? "#2d2a1f"
    : "#3d1f1f";

  const awardedColor = blocked
    ? "#6e7681"
    : fullPoints
    ? "#3fb950"
    : partialPoints
    ? "#d29922"
    : "#f85149";

  return (
    <div
      style={{
        background: "#161b22",
        border: `1px solid ${borderColor}`,
        borderRadius: 8,
        padding: "12px 16px",
        display: "flex",
        alignItems: "center",
        gap: 12,
      }}
    >
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 12, color: "#8b949e", fontWeight: 600, textTransform: "uppercase" }}>
          {metricLabel(result.metric)}
        </div>
        {result.actual !== undefined && result.actual !== null && (
          <div style={{ fontSize: 13, color: "#c9d1d9", marginTop: 2 }}>
            Actual: {formatActual(result.metric, result.actual)}
          </div>
        )}
        {result.partial_credit && !blocked && (
          <div style={{ fontSize: 12, color: "#d29922", marginTop: 2 }}>
            Partial credit applied
          </div>
        )}
        {noPoints && !blocked && (
          <div style={{ fontSize: 12, color: "#f85149", marginTop: 2 }}>
            Below threshold
          </div>
        )}
      </div>
      <div style={{ textAlign: "right", flexShrink: 0 }}>
        <span style={{ fontSize: 18, fontWeight: 700, color: awardedColor }}>
          {blocked ? "—" : result.awarded}
        </span>
        <span style={{ fontSize: 14, color: "#6e7681" }}>
          /{result.max_points} pts
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function CheckpointCards({ checkpointRules, ppa, gradeResult }: Props) {
  const hardRules = checkpointRules.hard ?? [];
  const scoredRules = checkpointRules.scored ?? [];

  // If no gradeResult — compute preview client-side
  const preview = !gradeResult ? computePreview(ppa, checkpointRules) : null;

  const hardResults: HardResult[] = gradeResult
    ? gradeResult.checkpoint_results.hard
    : (preview?.hard ?? []);

  const scoredResults: ScoredResult[] = gradeResult
    ? gradeResult.checkpoint_results.scored
    : (preview?.scored ?? []);

  const hardGateBlocked: boolean = gradeResult
    ? gradeResult.checkpoint_results.hard_gate_blocked
    : (preview?.hard_gate_blocked ?? false);

  const totalScore: number = gradeResult
    ? gradeResult.score
    : (preview?.total_score ?? 0);

  const maxScore = scoredRules.reduce((acc, r) => acc + r.points, 0);

  const isPreviewMode = !gradeResult;

  if (hardRules.length === 0 && scoredRules.length === 0) {
    return (
      <div style={{ color: "#6e7681", fontSize: 14, fontStyle: "italic" }}>
        No checkpoint criteria defined for this assignment.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {isPreviewMode && (
        <div
          style={{
            fontSize: 12,
            color: "#8b949e",
            background: "#0d1117",
            border: "1px solid #30363d",
            borderRadius: 6,
            padding: "8px 12px",
          }}
        >
          Preview — computed from your run metrics. Submit to receive an official grade.
        </div>
      )}

      {/* Hard gate criteria */}
      {hardResults.map((result, i) => (
        <HardGateCard key={`hard-${i}`} result={result} />
      ))}

      {/* Scored criteria */}
      {scoredResults.map((result, i) => (
        <ScoredCriterionCard
          key={`scored-${i}`}
          result={result}
          blocked={hardGateBlocked}
        />
      ))}

      {/* Score summary */}
      {(gradeResult || scoredRules.length > 0) && (
        <div
          style={{
            background: "#0d1117",
            border: "1px solid #30363d",
            borderRadius: 8,
            padding: "12px 16px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: 14, color: "#8b949e", fontWeight: 600 }}>
            {gradeResult ? "Final Score" : "Preview Score"}
          </span>
          <span>
            <span
              style={{
                fontSize: 22,
                fontWeight: 700,
                color: hardGateBlocked ? "#f85149" : "#3fb950",
              }}
            >
              {hardGateBlocked ? 0 : totalScore}
            </span>
            <span style={{ fontSize: 14, color: "#6e7681" }}>
              /{maxScore} pts
            </span>
          </span>
        </div>
      )}
    </div>
  );
}
