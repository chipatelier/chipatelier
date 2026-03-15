"""Wave 0 stubs for submission and leaderboard tests — Phase 2 plan 02-03 implements these."""
import pytest

from app.models.submission import Submission  # noqa: F401 — import to catch errors early


@pytest.mark.skip(reason="Wave 0 stub — implement in plan 02-03")
def test_locked_param_mismatch():
    """COUR-04: Submission is rejected if run config does not match locked params."""
    ...


@pytest.mark.skip(reason="Wave 0 stub — implement in plan 02-03")
def test_highest_score_retention():
    """COUR-04: Re-submission keeps the highest score, not the latest."""
    ...


@pytest.mark.skip(reason="Wave 0 stub — implement in plan 02-03")
def test_leaderboard_order():
    """DASH-01: Leaderboard returns submissions ordered by score descending."""
    ...


@pytest.mark.skip(reason="Wave 0 stub — implement in plan 02-03")
def test_leaderboard_anonymity():
    """DASH-01: Leaderboard response does not include student names or emails."""
    ...
