"""PPA metrics parsing tests — plan 01-09 (updated from plan 01-08).

Covers RSLT-01: parse_ppa_metrics reads ORFS per-stage JSON files and returns
a (ppa, stage_metrics) tuple with correct field mapping using real ORFS key names.

ORFS per-stage JSON format: logs/{platform}/{design}/base/*.json
Key format: {stage}__{category}__{metric}
Examples (verified real ORFS key names from CLAUDE.md):
  2_1_floorplan.json: {"floorplan__timing__setup__ws": 0.01, ...}
  5_1_grt.json: {"globalroute__timing__setup__ws": -0.5, ...}  # NOT route__
  5_2_route.json: {"detailedroute__route__drc_errors": 0, ...}
  6_report.json: {"finish__timing__setup__ws": 3.88, ...}       # NOT finish__design__violations
"""
import json
import uuid
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Tests: parse_ppa_metrics — per-stage JSON format (ORFS real output)
# ---------------------------------------------------------------------------

def test_parse_ppa_metrics_from_stage_json(tmp_path):
    """parse_ppa_metrics reads globalroute__timing__setup__ws from 5_1_grt.json correctly."""
    from app.services.metrics_service import parse_ppa_metrics

    # Create fixture per-stage JSON in ORFS logs directory structure
    log_dir = tmp_path / "logs" / "sky130hd" / "gcd" / "base"
    log_dir.mkdir(parents=True)

    # 5_1_grt.json — global route metrics (globalroute__ prefix, NOT route__)
    (log_dir / "5_1_grt.json").write_text(json.dumps({
        "globalroute__timing__setup__ws": -0.5,
        "globalroute__timing__setup__tns": -3.2,
    }))

    result, stage_metrics = parse_ppa_metrics(str(tmp_path), "sky130hd", "gcd")

    # Partial run (no finish stage) falls back to globalroute__ keys
    assert result["worst_negative_slack"] == -0.5
    assert result["total_negative_slack"] == -3.2


def test_parse_ppa_metrics_returns_tuple(tmp_path):
    """parse_ppa_metrics returns a tuple (ppa_dict, stage_metrics_dict), not a plain dict."""
    from app.services.metrics_service import parse_ppa_metrics

    log_dir = tmp_path / "logs" / "sky130hd" / "gcd" / "base"
    log_dir.mkdir(parents=True)
    (log_dir / "5_1_grt.json").write_text(json.dumps({
        "globalroute__timing__setup__ws": -0.1,
    }))

    result = parse_ppa_metrics(str(tmp_path), "sky130hd", "gcd")

    # Must return a tuple, not a dict
    assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    assert len(result) == 2
    ppa, stage_metrics = result
    assert isinstance(ppa, dict)
    assert isinstance(stage_metrics, dict)


def test_parse_ppa_metrics_stage_metrics_contains_raw_keys(tmp_path):
    """stage_metrics dict contains all raw keys from all per-stage JSON files merged."""
    from app.services.metrics_service import parse_ppa_metrics

    log_dir = tmp_path / "logs" / "sky130hd" / "gcd" / "base"
    log_dir.mkdir(parents=True)

    # Multiple stage JSON files
    (log_dir / "2_1_floorplan.json").write_text(json.dumps({
        "floorplan__timing__setup__ws": 0.01,
        "floorplan__design__core__area": 1070.65,
    }))
    (log_dir / "5_1_grt.json").write_text(json.dumps({
        "globalroute__timing__setup__ws": -0.3,
        "globalroute__timing__setup__tns": -1.5,
    }))

    ppa, stage_metrics = parse_ppa_metrics(str(tmp_path), "sky130hd", "gcd")

    # stage_metrics must contain ALL raw keys from ALL files
    assert "floorplan__timing__setup__ws" in stage_metrics
    assert "floorplan__design__core__area" in stage_metrics
    assert "globalroute__timing__setup__ws" in stage_metrics
    assert "globalroute__timing__setup__tns" in stage_metrics


def test_parse_ppa_metrics_fallback_empty_logs(tmp_path):
    """parse_ppa_metrics returns defaults without exception when logs dir is missing."""
    from app.services.metrics_service import parse_ppa_metrics

    # No logs directory created — expect defaults
    ppa, stage_metrics = parse_ppa_metrics(str(tmp_path), "sky130hd", "gcd")

    assert ppa["worst_negative_slack"] is None
    assert ppa["total_negative_slack"] is None
    assert ppa["drc_violations"] == 0  # default 0, not None
    assert ppa["core_area"] is None
    assert ppa["total_power"] is None
    assert ppa["flow_complete"] is False
    assert stage_metrics == {}


def test_parse_ppa_metrics_flow_complete_from_finish_report(tmp_path):
    """parse_ppa_metrics: flow_complete=True when 6_report.json has finish__timing__setup__ws."""
    from app.services.metrics_service import parse_ppa_metrics

    log_dir = tmp_path / "logs" / "sky130hd" / "gcd" / "base"
    log_dir.mkdir(parents=True)

    # 6_report.json — finish stage metrics (written by final_report.tcl)
    # finish__timing__setup__ws presence indicates full flow completed.
    # NOTE: finish__design__violations does NOT exist in real ORFS output.
    (log_dir / "6_report.json").write_text(json.dumps({
        "finish__timing__setup__ws": 3.88761,   # positive = timing met
        "finish__timing__setup__tns": 0,
        "finish__power__total": 0.002,
    }))

    ppa, stage_metrics = parse_ppa_metrics(str(tmp_path), "sky130hd", "gcd")

    # finish__timing__setup__ws present → flow completed
    assert ppa["flow_complete"] is True
    # finish metrics are used directly (primary key, no fallback needed)
    assert ppa["worst_negative_slack"] == 3.88761
    assert ppa["total_power"] == 0.002


def test_parse_ppa_metrics_flow_complete_false_without_finish(tmp_path):
    """parse_ppa_metrics: flow_complete=False for partial run without finish stage."""
    from app.services.metrics_service import parse_ppa_metrics

    log_dir = tmp_path / "logs" / "sky130hd" / "gcd" / "base"
    log_dir.mkdir(parents=True)

    # Only global route metrics — no finish stage
    (log_dir / "5_1_grt.json").write_text(json.dumps({
        "globalroute__timing__setup__ws": -2.42,
        "globalroute__timing__setup__tns": -99.7,
    }))

    ppa, stage_metrics = parse_ppa_metrics(str(tmp_path), "sky130hd", "gcd")

    # No finish__timing__setup__ws present → flow not complete
    assert ppa["flow_complete"] is False
    # Fallback to globalroute__ keys for partial run
    assert ppa["worst_negative_slack"] == -2.42
    assert ppa["total_negative_slack"] == -99.7


def test_parse_ppa_metrics_drc_from_detailedroute(tmp_path):
    """parse_ppa_metrics reads DRC errors from detailedroute__route__drc_errors."""
    from app.services.metrics_service import parse_ppa_metrics

    log_dir = tmp_path / "logs" / "sky130hd" / "gcd" / "base"
    log_dir.mkdir(parents=True)

    # 5_2_route.json — detailed route metrics with DRC errors
    (log_dir / "5_2_route.json").write_text(json.dumps({
        "detailedroute__route__drc_errors": 5,
        "detailedroute__route__wirelength": 37033,
    }))

    ppa, stage_metrics = parse_ppa_metrics(str(tmp_path), "sky130hd", "gcd")

    assert ppa["drc_violations"] == 5


def test_parse_ppa_metrics_drc_zero_when_absent(tmp_path):
    """parse_ppa_metrics returns drc_violations=0 when detailedroute key is absent."""
    from app.services.metrics_service import parse_ppa_metrics

    log_dir = tmp_path / "logs" / "sky130hd" / "gcd" / "base"
    log_dir.mkdir(parents=True)

    # No detailed route file — DRC should default to 0
    (log_dir / "5_1_grt.json").write_text(json.dumps({
        "globalroute__timing__setup__ws": -0.5,
    }))

    ppa, stage_metrics = parse_ppa_metrics(str(tmp_path), "sky130hd", "gcd")

    assert ppa["drc_violations"] == 0


def test_parse_ppa_metrics_finish_wins_over_globalroute(tmp_path):
    """parse_ppa_metrics: finish__timing__setup__ws takes priority over globalroute fallback."""
    from app.services.metrics_service import parse_ppa_metrics

    log_dir = tmp_path / "logs" / "sky130hd" / "gcd" / "base"
    log_dir.mkdir(parents=True)

    # Both global route and finish metrics present (full flow run)
    (log_dir / "5_1_grt.json").write_text(json.dumps({
        "globalroute__timing__setup__ws": -2.42,
        "globalroute__timing__setup__tns": -99.7,
    }))
    (log_dir / "6_report.json").write_text(json.dumps({
        "finish__timing__setup__ws": 3.88761,   # timing fixed after routing
        "finish__timing__setup__tns": 0,
        "finish__power__total": 7.3e-05,
    }))

    ppa, stage_metrics = parse_ppa_metrics(str(tmp_path), "sky130hd", "gcd")

    # finish__ keys take priority (primary signoff metrics)
    assert ppa["worst_negative_slack"] == 3.88761
    assert ppa["total_negative_slack"] == 0
    assert ppa["flow_complete"] is True


def test_metrics_service_wrapper_returns_tuple(tmp_path):
    """MetricsService.parse_from_workspace returns (ppa, stage_metrics) tuple."""
    from app.services.metrics_service import MetricsService

    log_dir = tmp_path / "logs" / "sky130hd" / "gcd" / "base"
    log_dir.mkdir(parents=True)
    (log_dir / "5_1_grt.json").write_text(json.dumps({
        "globalroute__timing__setup__ws": -0.1,
    }))

    svc = MetricsService()
    result = svc.parse_from_workspace(str(tmp_path), "sky130hd", "gcd")
    # Must return tuple
    assert isinstance(result, tuple)
    ppa, stage_metrics = result
    assert ppa["worst_negative_slack"] == -0.1
