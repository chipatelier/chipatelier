"""PPA metrics parsing from ORFS per-stage JSON output files.

ORFS writes one JSON file per stage in logs/{platform}/{design}/base/.
Key format: {stage}__{category}__{metric}
Example: route__timing__setup__ws, finish__design__violations

Reference: CLAUDE.md "Real ORFS Metrics Schema" section.
"""
import json
from pathlib import Path


def parse_ppa_metrics(workspace: str, platform: str, design: str) -> tuple[dict, dict]:
    """Parse all per-stage ORFS JSON metric files from logs/{platform}/{design}/base/*.json.

    ORFS writes one JSON file per stage (e.g. 2_1_floorplan.json, 5_1_grt.json,
    6_report.json). Each file uses the key format: {stage}__{category}__{metric}.
    Example: "floorplan__timing__setup__ws", "route__timing__setup__tns"

    Returns:
        ppa: dict — friendly-name mapped subset for runs.ppa JSONB column
        stage_metrics: dict — raw merged dict of ALL keys for runs.stage_metrics JSONB column

    Reference: CLAUDE.md "Real ORFS Metrics Schema" section.
    """
    ppa: dict = {
        "worst_negative_slack": None,
        "total_negative_slack": None,
        "drc_violations": 0,
        "core_area": None,
        "total_power": None,
        "flow_complete": False,
    }
    stage_metrics: dict = {}

    logs_dir = Path(workspace) / "logs" / platform / design / "base"
    if not logs_dir.exists():
        return ppa, stage_metrics

    # Merge all per-stage JSON files in sorted order so later stages (higher numbers)
    # override earlier stages for overlapping keys.
    for json_file in sorted(logs_dir.glob("*.json")):
        try:
            data = json.loads(json_file.read_text())
            if isinstance(data, dict):
                stage_metrics.update(data)
        except (json.JSONDecodeError, OSError):
            pass  # skip malformed files — do not crash

    if not stage_metrics:
        return ppa, stage_metrics

    # Map raw ORFS keys to friendly names for the ppa column.
    # Route metrics preferred over finish for WNS/TNS (finish may not exist for partial runs).
    # finish__design__violations being present (not None) indicates the full flow ran.
    ppa.update({
        "worst_negative_slack": stage_metrics.get(
            "route__timing__setup__ws",
            stage_metrics.get("finish__timing__setup__ws"),
        ),
        "total_negative_slack": stage_metrics.get(
            "route__timing__setup__tns",
            stage_metrics.get("finish__timing__setup__tns"),
        ),
        "core_area": stage_metrics.get("floorplan__design__core__area"),
        "drc_violations": int(stage_metrics.get("finish__design__violations", 0) or 0),
        "total_power": stage_metrics.get(
            "finish__power__total",
            stage_metrics.get("route__power__total"),
        ),
        "flow_complete": stage_metrics.get("finish__design__violations") is not None,
    })

    return ppa, stage_metrics


class MetricsService:
    """Service wrapper for dependency injection."""

    def parse_from_workspace(
        self, workspace: str, platform: str, design: str
    ) -> tuple[dict, dict]:
        """Parse PPA metrics from workspace. Returns (ppa, stage_metrics) tuple."""
        return parse_ppa_metrics(workspace, platform, design)
