"""
Log parsing utilities for ORFS stage detection and separator formatting.

Stage detection uses regex patterns against log lines from the ORFS toolchain.
ORFS flow.sh prints a reliable marker before every stage:
    Running <script>.tcl, stage <stage_id>
Examples:
    Running floorplan.tcl, stage 2_1_floorplan
    Running cts.tcl, stage 4_1_cts
    Running global_route.tcl, stage 5_1_grt
    Running final_report.tcl, stage 6_report

The stage_id maps directly to the JSON metrics filename.
"""
import re

# ---------------------------------------------------------------------------
# Stage transition pattern
# Matches the reliable "Running <script>.tcl, stage <stage_id>" format
# printed by flow.sh before every stage invocation.
# ---------------------------------------------------------------------------

_STAGE_LINE_RE = re.compile(r"Running\s+\S+\.tcl,\s+stage\s+(\S+)")

# Map stage_id prefixes to friendly stage names
_STAGE_ID_MAP: dict[str, str] = {
    "1_1_yosys":      "synthesis",
    "1_2_yosys":      "synthesis",
    "2_1_floorplan":  "floorplan",
    "3_1_place":      "place",
    "3_3_place":      "place",
    "3_4_place":      "place",
    "3_5_place":      "place",
    "4_1_cts":        "cts",
    "5_1_grt":        "route",
    "5_2_route":      "route",
    "5_3_fillcell":   "route",
    "6_report":       "finish",
    "6_1_merge":      "finish",
}

# Separator format — the ═══ character is used so frontend can detect it visually
SEPARATOR_FMT = "═══ {stage} ══════════════════════════════════"


def detect_stage(line: str) -> str | None:
    """Return the ORFS stage name if `line` is a stage transition marker, else None.

    Parses the reliable "Running <script>.tcl, stage <stage_id>" format
    printed by ORFS flow.sh before every stage.

    Args:
        line: A single log line from ORFS stdout.

    Returns:
        One of: "synthesis", "floorplan", "place", "cts", "route", "finish",
        or None if the line is not a stage transition marker.
    """
    m = _STAGE_LINE_RE.search(line)
    if not m:
        return None
    stage_id = m.group(1)
    # Exact match first, then try prefix match
    if stage_id in _STAGE_ID_MAP:
        return _STAGE_ID_MAP[stage_id]
    # Prefix-based fallback for sub-stages not explicitly listed
    for prefix, stage in _STAGE_ID_MAP.items():
        if stage_id.startswith(prefix.split("_")[0] + "_"):
            return stage
    return None


def format_stage_separator(stage: str) -> str:
    """Return a visual separator line for a stage transition.

    Args:
        stage: Stage name (e.g., "synthesis"). Will be uppercased in output.

    Returns:
        A separator string starting with ═══ for terminal visual distinction.
    """
    return SEPARATOR_FMT.format(stage=stage.upper())
