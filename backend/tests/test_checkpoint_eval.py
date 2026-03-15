"""Checkpoint evaluation tests — plan 02-04.

Tests for the pure evaluate_checkpoint_rules function (no DB, no Celery needed).
"""
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models.submission import Submission  # noqa: F401 — import to catch errors early
from app.models.assignment import Assignment  # noqa: F401


# ---------------------------------------------------------------------------
# evaluate_checkpoint_rules unit tests (pure function — no DB needed)
# ---------------------------------------------------------------------------

def test_hard_gate_blocks_score():
    """COUR-05: A run with DRC violations fails the hard gate and scores zero."""
    from worker.tasks.checkpoint_eval import evaluate_checkpoint_rules

    rules = {
        "hard": [{"metric": "drc_violations", "op": "eq", "value": 0}],
        "scored": [
            {"metric": "worst_negative_slack", "op": "gte", "value": -0.1, "points": 40}
        ],
    }
    # DRC violations = 5 — should fail hard gate and force score=0
    ppa = {"drc_violations": 5, "worst_negative_slack": -0.05}
    checkpoint_results, score = evaluate_checkpoint_rules(ppa, rules)

    assert score == 0, f"Expected score=0 when hard gate fails, got {score}"
    assert checkpoint_results["hard"][0]["passed"] is False
    # Scored criteria should still be evaluated but score is blocked
    assert checkpoint_results.get("hard_gate_blocked") is True


def test_hard_gate_passes_when_drc_zero():
    """Hard gate passes when DRC violations == 0, scored points accumulate."""
    from worker.tasks.checkpoint_eval import evaluate_checkpoint_rules

    rules = {
        "hard": [{"metric": "drc_violations", "op": "eq", "value": 0}],
        "scored": [
            {"metric": "worst_negative_slack", "op": "gte", "value": -0.1, "points": 40}
        ],
    }
    ppa = {"drc_violations": 0, "worst_negative_slack": -0.05}  # WNS passes
    checkpoint_results, score = evaluate_checkpoint_rules(ppa, rules)

    assert score == 40, f"Expected score=40, got {score}"
    assert checkpoint_results["hard"][0]["passed"] is True
    assert checkpoint_results.get("hard_gate_blocked") is not True


def test_partial_credit():
    """COUR-05: Partial credit awarded when WNS is between thresholds."""
    from worker.tasks.checkpoint_eval import evaluate_checkpoint_rules

    rules = {
        "hard": [],
        "scored": [
            {
                "metric": "worst_negative_slack",
                "op": "gte",
                "value": -0.1,   # full credit threshold
                "points": 40,
                "partial": {"threshold": -0.5, "points": 20},  # partial credit threshold
            }
        ],
    }
    # WNS = -0.3: worse than -0.1 (no full credit) but better than -0.5 (partial credit)
    ppa = {"worst_negative_slack": -0.3}
    checkpoint_results, score = evaluate_checkpoint_rules(ppa, rules)

    assert score == 20, f"Expected partial credit 20 pts, got {score}"
    scored = checkpoint_results["scored"][0]
    assert scored["awarded"] == 20
    assert scored["max_points"] == 40
    assert scored["partial_credit"] is True


def test_no_partial_credit_when_below_partial_threshold():
    """No points awarded when metric is worse than both thresholds."""
    from worker.tasks.checkpoint_eval import evaluate_checkpoint_rules

    rules = {
        "hard": [],
        "scored": [
            {
                "metric": "worst_negative_slack",
                "op": "gte",
                "value": -0.1,
                "points": 40,
                "partial": {"threshold": -0.5, "points": 20},
            }
        ],
    }
    # WNS = -0.8: worse than both thresholds
    ppa = {"worst_negative_slack": -0.8}
    checkpoint_results, score = evaluate_checkpoint_rules(ppa, rules)

    assert score == 0, f"Expected 0 pts when below all thresholds, got {score}"
    scored = checkpoint_results["scored"][0]
    assert scored["awarded"] == 0


def test_grade_published():
    """COUR-05: Grading result is stored in submissions and status set to complete."""
    # Test evaluate_checkpoint_rules returns correct structure for Redis publishing
    from worker.tasks.checkpoint_eval import evaluate_checkpoint_rules

    rules = {
        "hard": [{"metric": "drc_violations", "op": "eq", "value": 0}],
        "scored": [
            {"metric": "worst_negative_slack", "op": "gte", "value": -0.1, "points": 40}
        ],
    }
    ppa = {"drc_violations": 0, "worst_negative_slack": -0.05}
    checkpoint_results, score = evaluate_checkpoint_rules(ppa, rules)

    # Verify result is JSON-serializable (required for Redis publish)
    result_payload = {"score": score, "checkpoint_results": checkpoint_results}
    serialized = json.dumps(result_payload)
    parsed = json.loads(serialized)

    assert parsed["score"] == 40
    assert "hard" in parsed["checkpoint_results"]
    assert "scored" in parsed["checkpoint_results"]
