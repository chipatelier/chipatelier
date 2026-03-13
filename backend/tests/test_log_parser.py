"""
JOB-04 unit tests for the log_parser service.
Tests stage detection and separator formatting.
"""
import pytest

from app.services.log_parser import detect_stage, format_stage_separator


# ---------------------------------------------------------------------------
# detect_stage tests
# ---------------------------------------------------------------------------

def test_detect_stage_synthesis_starting():
    """detect_stage recognizes synthesis start line."""
    assert detect_stage("Starting synthesis in OpenROAD...") == "synthesis"


def test_detect_stage_synthesis_finished():
    """detect_stage recognizes synthesis finish line."""
    assert detect_stage("Finished synthesis step") == "synthesis"


def test_detect_stage_route_starting():
    """detect_stage recognizes routing start line."""
    assert detect_stage("Starting routing phase") == "route"


def test_detect_stage_route_finished():
    """detect_stage recognizes routing finish line."""
    assert detect_stage("Finished routing") == "route"


def test_detect_stage_floorplan():
    """detect_stage recognizes floorplan lines."""
    assert detect_stage("Starting floorplan step") == "floorplan"


def test_detect_stage_place():
    """detect_stage recognizes placement lines."""
    assert detect_stage("Starting placement optimization") == "place"


def test_detect_stage_cts():
    """detect_stage recognizes CTS lines."""
    assert detect_stage("Starting cts phase") == "cts"


def test_detect_stage_gds():
    """detect_stage recognizes GDS/final lines."""
    assert detect_stage("Starting final gds export") == "gds"


def test_detect_stage_no_match():
    """detect_stage returns None for unrelated log lines."""
    assert detect_stage("random log line from design tool") is None


def test_detect_stage_empty_line():
    """detect_stage returns None for empty line."""
    assert detect_stage("") is None


def test_detect_stage_case_insensitive():
    """detect_stage is case-insensitive."""
    assert detect_stage("STARTING SYNTHESIS") == "synthesis"
    assert detect_stage("FINISHED ROUTING") == "route"


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
    result = format_stage_separator("GDS")
    assert "GDS" in result
