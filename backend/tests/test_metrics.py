"""PPA metrics parsing tests — plan 01-08 (updated from plan 01-05).

Covers RSLT-01: parse_ppa_metrics reads ORFS per-stage JSON files and returns
a (ppa, stage_metrics) tuple with correct field mapping.

ORFS per-stage JSON format: logs/{platform}/{design}/base/*.json
Key format: {stage}__{category}__{metric}
Examples:
  2_1_floorplan.json: {"floorplan__timing__setup__ws": 0.01, ...}
  5_1_grt.json: {"route__timing__setup__ws": -0.5, ...}
  6_report.json: {"finish__design__violations": 0, ...}
"""
import json
import uuid
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Tests: parse_ppa_metrics — per-stage JSON format (ORFS real output)
# ---------------------------------------------------------------------------

def test_parse_ppa_metrics_from_stage_json(tmp_path):
    """parse_ppa_metrics reads route__timing__setup__ws from 5_1_grt.json correctly."""
    from app.services.metrics_service import parse_ppa_metrics

    # Create fixture per-stage JSON in ORFS logs directory structure
    log_dir = tmp_path / "logs" / "sky130hd" / "gcd" / "base"
    log_dir.mkdir(parents=True)

    # 5_1_grt.json — global route metrics (route__ prefix)
    (log_dir / "5_1_grt.json").write_text(json.dumps({
        "route__timing__setup__ws": -0.5,
        "route__timing__setup__tns": -3.2,
        "route__power__total": 0.0043,
    }))

    result, stage_metrics = parse_ppa_metrics(str(tmp_path), "sky130hd", "gcd")

    assert result["worst_negative_slack"] == -0.5
    assert result["total_negative_slack"] == -3.2
    assert result["total_power"] == 0.0043


def test_parse_ppa_metrics_returns_tuple(tmp_path):
    """parse_ppa_metrics returns a tuple (ppa_dict, stage_metrics_dict), not a plain dict."""
    from app.services.metrics_service import parse_ppa_metrics

    log_dir = tmp_path / "logs" / "sky130hd" / "gcd" / "base"
    log_dir.mkdir(parents=True)
    (log_dir / "5_1_grt.json").write_text(json.dumps({
        "route__timing__setup__ws": -0.1,
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
        "route__timing__setup__ws": -0.3,
        "route__timing__setup__tns": -1.5,
    }))

    ppa, stage_metrics = parse_ppa_metrics(str(tmp_path), "sky130hd", "gcd")

    # stage_metrics must contain ALL raw keys from ALL files
    assert "floorplan__timing__setup__ws" in stage_metrics
    assert "floorplan__design__core__area" in stage_metrics
    assert "route__timing__setup__ws" in stage_metrics
    assert "route__timing__setup__tns" in stage_metrics


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
    """parse_ppa_metrics: flow_complete=True when 6_report.json has finish__design__violations."""
    from app.services.metrics_service import parse_ppa_metrics

    log_dir = tmp_path / "logs" / "sky130hd" / "gcd" / "base"
    log_dir.mkdir(parents=True)

    # 6_report.json — finish stage metrics
    (log_dir / "6_report.json").write_text(json.dumps({
        "finish__design__violations": 0,
        "finish__timing__setup__ws": -0.05,
        "finish__power__total": 0.002,
    }))

    ppa, stage_metrics = parse_ppa_metrics(str(tmp_path), "sky130hd", "gcd")

    # finish__design__violations present (even if 0) means flow completed
    assert ppa["flow_complete"] is True
    assert ppa["drc_violations"] == 0
    # finish metrics fall back when route metrics not present
    assert ppa["worst_negative_slack"] == -0.05
    assert ppa["total_power"] == 0.002


def test_metrics_service_wrapper_returns_tuple(tmp_path):
    """MetricsService.parse_from_workspace returns (ppa, stage_metrics) tuple."""
    from app.services.metrics_service import MetricsService

    log_dir = tmp_path / "logs" / "sky130hd" / "gcd" / "base"
    log_dir.mkdir(parents=True)
    (log_dir / "5_1_grt.json").write_text(json.dumps({"route__timing__setup__ws": -0.1}))

    svc = MetricsService()
    result = svc.parse_from_workspace(str(tmp_path), "sky130hd", "gcd")
    # Must return tuple
    assert isinstance(result, tuple)
    ppa, stage_metrics = result
    assert ppa["worst_negative_slack"] == -0.1
