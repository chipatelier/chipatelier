"""
Log parsing utilities for ORFS stage detection and separator formatting.

Stage detection uses regex patterns against log lines from the ORFS toolchain.
Patterns are calibrated against known ORFS log output; if no stage transition
is detected in the first 200 lines, a warning is logged for pattern calibration.

NOTE: The exact ORFS log format for stage boundaries is an open question.
These patterns are initial hypotheses. During real ORFS runs, unmatched lines
should be logged so patterns can be refined.
"""
import re

# ---------------------------------------------------------------------------
# Stage transition patterns
# Matches "Starting X" or "Finished X" log lines for each ORFS stage.
# ---------------------------------------------------------------------------

STAGE_PATTERNS: dict[str, re.Pattern[str]] = {
    "synthesis": re.compile(r"(Starting|Finished)\s+synthesis", re.IGNORECASE),
    "floorplan": re.compile(r"(Starting|Finished)\s+floorplan", re.IGNORECASE),
    "place":     re.compile(r"(Starting|Finished)\s+placement", re.IGNORECASE),
    "cts":       re.compile(r"(Starting|Finished)\s+cts", re.IGNORECASE),
    "route":     re.compile(r"(Starting|Finished)\s+routing", re.IGNORECASE),
    "gds":       re.compile(r"(Starting|Finished)\s+final", re.IGNORECASE),
}

# Separator format — the ═══ character is used so frontend can detect it visually
SEPARATOR_FMT = "═══ {stage} ══════════════════════════════════"


def detect_stage(line: str) -> str | None:
    """Return the ORFS stage name if `line` is a stage transition marker, else None.

    Args:
        line: A single log line from ORFS stdout.

    Returns:
        One of: "synthesis", "floorplan", "place", "cts", "route", "gds", or None.
    """
    for stage, pattern in STAGE_PATTERNS.items():
        if pattern.search(line):
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
