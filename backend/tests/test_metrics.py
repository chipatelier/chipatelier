"""PPA metrics parsing tests — plan 01-05.

Covers RSLT-01: parse_ppa_metrics reads ORFS metadata.json and returns correct field mapping.
"""
import json
import uuid
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Tests: parse_ppa_metrics
# ---------------------------------------------------------------------------

def test_parse_ppa_metrics_from_metadata_json(tmp_path):
    """parse_ppa_metrics reads timing__setup__ws and other METRICS2.1 keys correctly."""
    from app.services.metrics_service import parse_ppa_metrics

    # Create fixture metadata.json in expected ORFS layout
    log_dir = tmp_path / "logs" / "sky130hd" / "gcd"
    log_dir.mkdir(parents=True)
    metadata = {
        "timing__setup__ws": -0.5,
        "timing__setup__tns": -3.2,
        "route__drc_errors__count": 0,
        "design__instance__area": 12345.67,
        "power__total": 0.0043,
        "flow__platform__status": "succeeded",
    }
    (log_dir / "metadata.json").write_text(json.dumps(metadata))

    result = parse_ppa_metrics(str(tmp_path), "sky130hd", "gcd")

    assert result["worst_negative_slack"] == -0.5
    assert result["total_negative_slack"] == -3.2
    assert result["drc_violations"] == 0
    assert result["core_area"] == 12345.67
    assert result["total_power"] == 0.0043
    assert result["flow_complete"] is True


def test_parse_ppa_metrics_fallback_missing_file(tmp_path):
    """parse_ppa_metrics returns all-None defaults when metadata.json is missing."""
    from app.services.metrics_service import parse_ppa_metrics

    # No metadata.json created — expect defaults
    result = parse_ppa_metrics(str(tmp_path), "sky130hd", "gcd")

    assert result["worst_negative_slack"] is None
    assert result["total_negative_slack"] is None
    assert result["drc_violations"] == 0  # default 0, not None
    assert result["core_area"] is None
    assert result["total_power"] is None
    assert result["flow_complete"] is False


def test_parse_ppa_metrics_flow_incomplete(tmp_path):
    """parse_ppa_metrics returns flow_complete=False when status is not 'succeeded'."""
    from app.services.metrics_service import parse_ppa_metrics

    log_dir = tmp_path / "logs" / "sky130hd" / "gcd"
    log_dir.mkdir(parents=True)
    metadata = {
        "timing__setup__ws": -1.0,
        "route__drc_errors__count": 5,
        "flow__platform__status": "failed",
    }
    (log_dir / "metadata.json").write_text(json.dumps(metadata))

    result = parse_ppa_metrics(str(tmp_path), "sky130hd", "gcd")

    assert result["flow_complete"] is False
    assert result["drc_violations"] == 5


def test_parse_ppa_metrics_malformed_json(tmp_path):
    """parse_ppa_metrics returns defaults without exception when metadata.json is malformed."""
    from app.services.metrics_service import parse_ppa_metrics

    log_dir = tmp_path / "logs" / "sky130hd" / "gcd"
    log_dir.mkdir(parents=True)
    (log_dir / "metadata.json").write_text("this is not valid json {{{")

    # Must not raise
    result = parse_ppa_metrics(str(tmp_path), "sky130hd", "gcd")
    assert result["worst_negative_slack"] is None
    assert result["flow_complete"] is False


def test_metrics_service_wrapper(tmp_path):
    """MetricsService.parse_from_workspace delegates to parse_ppa_metrics."""
    from app.services.metrics_service import MetricsService

    log_dir = tmp_path / "logs" / "sky130hd" / "gcd"
    log_dir.mkdir(parents=True)
    (log_dir / "metadata.json").write_text(json.dumps({"timing__setup__ws": -0.1}))

    svc = MetricsService()
    result = svc.parse_from_workspace(str(tmp_path), "sky130hd", "gcd")
    assert result["worst_negative_slack"] == -0.1
