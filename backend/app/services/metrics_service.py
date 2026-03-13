"""PPA metrics parsing from ORFS output files.

Parses the METRICS2.1 format metadata.json produced by OpenROAD Flow Scripts.
Reference: https://openroad-flow-scripts.readthedocs.io/en/latest/contrib/Metrics.html

Key mappings (verified against ORFS METRICS2.1 spec — verify against actual run
output during integration testing as key names may vary slightly by ORFS version):
  timing__setup__ws        → worst_negative_slack (WNS) in nanoseconds
  timing__setup__tns       → total_negative_slack (TNS) in nanoseconds
  route__drc_errors__count → drc_violations (integer count)
  design__instance__area   → core_area in µm²
  power__total             → total_power in Watts
  flow__platform__status   → flow_complete (True if "succeeded")
"""
import json
from pathlib import Path


def parse_ppa_metrics(workspace: str, platform: str, design: str) -> dict:
    """Parse PPA metrics from ORFS metadata.json.

    Primary source: logs/{platform}/{design}/metadata.json (METRICS2.1 format).
    Returns defaults (None/False/0) without raising if file is missing or malformed.

    Args:
        workspace: Path to the ORFS workspace directory.
        platform: ORFS platform name (e.g., "sky130hd").
        design: Design name (e.g., "gcd").

    Returns:
        Dict with keys: worst_negative_slack, total_negative_slack,
        drc_violations, core_area, total_power, flow_complete.
    """
    result = {
        "worst_negative_slack": None,
        "total_negative_slack": None,
        "drc_violations": 0,
        "core_area": None,
        "total_power": None,
        "flow_complete": False,
    }
    metadata_path = Path(workspace) / "logs" / platform / design / "metadata.json"
    if metadata_path.exists():
        try:
            data = json.loads(metadata_path.read_text())
            result.update({
                "worst_negative_slack": data.get("timing__setup__ws"),
                "total_negative_slack": data.get("timing__setup__tns"),
                "drc_violations": int(data.get("route__drc_errors__count", 0) or 0),
                "core_area": data.get("design__instance__area"),
                "total_power": data.get("power__total"),
                "flow_complete": data.get("flow__platform__status") == "succeeded",
            })
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass  # return defaults on parse error — do not crash
    return result


class MetricsService:
    """Service wrapper for dependency injection."""

    def parse_from_workspace(self, workspace: str, platform: str, design: str) -> dict:
        """Parse PPA metrics from workspace. Delegates to parse_ppa_metrics."""
        return parse_ppa_metrics(workspace, platform, design)
