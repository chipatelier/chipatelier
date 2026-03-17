"""
JOB-04 unit tests for the log_parser service.
Tests stage detection and separator formatting.

Stage detection parses the reliable ORFS format:
    Running <script>.tcl, stage <stage_id>
"""
import pytest

from app.services.log_parser import detect_stage, format_stage_separator


# ---------------------------------------------------------------------------
# detect_stage tests — real ORFS log lines
# ---------------------------------------------------------------------------

def test_detect_stage_synthesis():
    """detect_stage recognizes synthesis stage line."""
    assert detect_stage("Running yosys.tcl, stage 1_2_yosys") == "synthesis"


def test_detect_stage_synthesis_canonicalize():
    """detect_stage recognizes synthesis canonicalize sub-stage."""
    assert detect_stage("Running yosys_canonicalize.tcl, stage 1_1_yosys") == "synthesis"


def test_detect_stage_floorplan():
    """detect_stage recognizes floorplan stage line."""
    assert detect_stage("Running floorplan.tcl, stage 2_1_floorplan") == "floorplan"


def test_detect_stage_place():
    """detect_stage recognizes placement stage line."""
    assert detect_stage("Running global_place.tcl, stage 3_3_place_gp") == "place"


def test_detect_stage_place_dp():
    """detect_stage recognizes detail placement stage line."""
    assert detect_stage("Running detail_place.tcl, stage 3_5_place_dp") == "place"


def test_detect_stage_cts():
    """detect_stage recognizes CTS stage line."""
    assert detect_stage("Running cts.tcl, stage 4_1_cts") == "cts"


def test_detect_stage_global_route():
    """detect_stage recognizes global route stage line."""
    assert detect_stage("Running global_route.tcl, stage 5_1_grt") == "route"


def test_detect_stage_detail_route():
    """detect_stage recognizes detail route stage line."""
    assert detect_stage("Running detail_route.tcl, stage 5_2_route") == "route"


def test_detect_stage_finish():
    """detect_stage recognizes final report stage line."""
    assert detect_stage("Running final_report.tcl, stage 6_report") == "finish"


def test_detect_stage_no_match():
    """detect_stage returns None for unrelated log lines."""
    assert detect_stage("random log line from design tool") is None


def test_detect_stage_empty_line():
    """detect_stage returns None for empty line."""
    assert detect_stage("") is None


def test_detect_stage_openroad_info_line():
    """detect_stage returns None for normal OpenROAD log lines."""
    assert detect_stage("[INFO FLW-0012] Running floorplan...") is None


# ---------------------------------------------------------------------------
# format_stage_separator tests
# ---------------------------------------------------------------------------

def test_format_stage_separator_synthesis():
    """format_stage_separator produces upper-cased separator for synthesis."""
    result = format_stage_separator("synthesis")
    assert "SYNTHESIS" in result
    assert result.startswith("═══")


def test_format_stage_separator_route():
    """format_stage_separator works for route stage."""
    result = format_stage_separator("route")
    assert "ROUTE" in result
    assert result.startswith("═══")


def test_format_stage_separator_uppercase_input():
    """format_stage_separator handles uppercase stage name."""
    result = format_stage_separator("FINISH")
    assert "FINISH" in result
