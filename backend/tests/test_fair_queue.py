"""Tests for per-student fair queue (Redis sorted-set based).

Uses fakeredis for isolation — no real Redis needed.
"""
import pytest
import fakeredis

from worker.tasks.fair_queue import (
    enqueue_student_job,
    claim_next_job,
    get_student_queue_depth,
    release_student_slot,
)


@pytest.fixture
def r():
    return fakeredis.FakeRedis()


def test_enqueue_single_student(r):
    """Enqueue one job for a student; depth increments; claim returns that job."""
    enqueue_student_job("student-1", "run-A", r)
    assert get_student_queue_depth("student-1", r) == 1
    next_run = claim_next_job(r)
    assert next_run == "run-A"


def test_fair_ordering_two_students(r):
    """Student-2 with fewer queued runs gets dispatched before student-1's later-queued jobs."""
    # student-1 enqueues 3 jobs first (scores: 0, 1, 2)
    for i in range(3):
        enqueue_student_job("student-1", f"run-1-{i}", r)
    # student-2 enqueues 1 job — score=0 (same as student-1's first, but run-1-2 has score=2)
    enqueue_student_job("student-2", "run-2-0", r)
    # Drain all jobs and collect the order; student-1's run-1-2 (score=2) must come AFTER
    # student-2's run-2-0 (score=0) since student-2 had fewer queued runs at submission time
    claimed_all = []
    while True:
        job = claim_next_job(r)
        if job is None:
            break
        claimed_all.append(job)
    assert len(claimed_all) == 4
    # student-2's job (score=0) must come before student-1's later jobs (score=1 and score=2)
    idx_2 = claimed_all.index("run-2-0")
    idx_1_1 = claimed_all.index("run-1-1")
    idx_1_2 = claimed_all.index("run-1-2")
    assert idx_2 < idx_1_1, "student-2 run should come before student-1's second job"
    assert idx_2 < idx_1_2, "student-2 run should come before student-1's third job"


def test_empty_queue_returns_none(r):
    """claim_next_job returns None when the sorted set is empty."""
    assert claim_next_job(r) is None


def test_release_slot_decrements_depth(r):
    """release_student_slot decrements the depth counter back to 0."""
    enqueue_student_job("student-1", "run-A", r)
    assert get_student_queue_depth("student-1", r) == 1
    release_student_slot("student-1", r)
    assert get_student_queue_depth("student-1", r) == 0


def test_depth_zero_does_not_go_negative(r):
    """release_student_slot does not decrement below 0."""
    # No jobs enqueued — depth is already 0
    release_student_slot("student-X", r)
    assert get_student_queue_depth("student-X", r) == 0


def test_multiple_jobs_same_student_score_increases(r):
    """Each additional job from the same student gets a higher score (queued behind)."""
    enqueue_student_job("student-1", "run-A", r)  # score=0, depth becomes 1
    enqueue_student_job("student-1", "run-B", r)  # score=1, depth becomes 2
    # student-2 enqueues one job with score=0 (same as run-A)
    enqueue_student_job("student-2", "run-2-0", r)  # score=0, depth becomes 1
    # run-B has score=1 — it must always come after both run-A and run-2-0 (both score=0)
    claimed_all = []
    while True:
        job = claim_next_job(r)
        if job is None:
            break
        claimed_all.append(job)
    assert len(claimed_all) == 3
    # run-B (score=1) must be last
    assert claimed_all[-1] == "run-B", "run-B (score=1) must come last"
    # run-A and run-2-0 both have score=0 — both should come before run-B
    assert "run-A" in claimed_all[:2]
    assert "run-2-0" in claimed_all[:2]
