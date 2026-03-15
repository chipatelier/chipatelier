"""Wave 0 stubs for checkpoint evaluation tests — Phase 2 plan 02-03 implements these."""
import pytest

from app.models.submission import Submission  # noqa: F401 — import to catch errors early
from app.models.assignment import Assignment  # noqa: F401


@pytest.mark.skip(reason="Wave 0 stub — implement in plan 02-03")
def test_hard_gate_blocks_score():
    """COUR-05: A run with DRC violations fails the hard gate and scores zero."""
    ...


@pytest.mark.skip(reason="Wave 0 stub — implement in plan 02-03")
def test_partial_credit():
    """COUR-05: Partial credit awarded when WNS is between thresholds."""
    ...


@pytest.mark.skip(reason="Wave 0 stub — implement in plan 02-03")
def test_grade_published():
    """COUR-05: Grading result is stored in submissions and status set to complete."""
    ...
