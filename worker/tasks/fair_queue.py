"""
Fair queue implementation using Redis sorted sets.

Key design:
  ZADD fair_queue {score} {run_id}
    score = get_student_queue_depth(student_id) at time of submission
    Lower score = dispatched first.
    Same-student runs stack at the same or incrementing score.
    Different students with fewer queued runs get lower scores = priority.

This prevents one student with 10 queued runs from starving others.
Instructor jobs bypass this queue entirely (high_priority Celery queue).

Sorted set key: "fair_queue:normal"
Student depth key: "fair_queue:depth:{student_id}"  (integer, INCR/DECR)
"""
import redis as redis_lib

FAIR_QUEUE_KEY = "fair_queue:normal"


def get_student_queue_depth(student_id: str, r: redis_lib.Redis) -> int:
    """Return count of runs currently in the fair queue for this student."""
    val = r.get(f"fair_queue:depth:{student_id}")
    return int(val) if val else 0


def enqueue_student_job(student_id: str, run_id: str, r: redis_lib.Redis) -> float:
    """Add run_id to fair queue with score = current depth for this student.

    Students with fewer queued runs get lower scores and are dispatched first.
    Returns the score assigned to this job.
    """
    score = get_student_queue_depth(student_id, r)
    r.zadd(FAIR_QUEUE_KEY, {run_id: float(score)})
    r.incr(f"fair_queue:depth:{student_id}")
    r.expire(f"fair_queue:depth:{student_id}", 86400)  # 24hr TTL on depth key
    return float(score)


def claim_next_job(r: redis_lib.Redis) -> str | None:
    """Atomically pop the run_id with the lowest score (next to run).

    Returns the run_id string, or None if the queue is empty.
    """
    result = r.zpopmin(FAIR_QUEUE_KEY, 1)
    if not result:
        return None
    run_id, _score = result[0]
    return run_id.decode() if isinstance(run_id, bytes) else run_id


def release_student_slot(student_id: str, r: redis_lib.Redis) -> None:
    """Decrement depth counter when a job finishes.

    Call from orfs_job finally block to update fair queue accounting.
    Does not decrement below zero.
    """
    current = get_student_queue_depth(student_id, r)
    if current > 0:
        r.decr(f"fair_queue:depth:{student_id}")


# ---------------------------------------------------------------------------
# Celery beat task — drain fair queue into orfs_jobs Celery queue
# ---------------------------------------------------------------------------

try:
    from celery_app import app as _celery_app

    @_celery_app.task(name="worker.tasks.fair_queue.drain_queue", queue="background")
    def drain_queue():
        """
        Celery beat task (every 5s): dispatch up to MAX_CONCURRENT_JOBS - current_running jobs.
        Pops from fair_queue sorted set and sends to run_orfs_job Celery task.
        Only dispatches if there is capacity (running job count < MAX_CONCURRENT_JOBS).
        """
        from app.core.config import get_settings
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import Session

        settings = get_settings()
        r = redis_lib.Redis.from_url(settings.REDIS_URL)
        sync_url = settings.DATABASE_URL.replace(
            "postgresql+asyncpg://", "postgresql://"
        ).replace("sqlite+aiosqlite://", "sqlite://")
        engine = create_engine(sync_url)

        with Session(engine) as db:
            running_count = db.execute(
                text("SELECT COUNT(*) FROM runs WHERE status IN ('starting', 'running')")
            ).scalar()
            capacity = settings.MAX_CONCURRENT_JOBS - (running_count or 0)

        for _ in range(max(0, capacity)):
            run_id = claim_next_job(r)
            if run_id is None:
                break
            # Dispatch to Celery orfs_jobs queue
            from tasks.orfs_job import run_orfs_job
            run_orfs_job.apply_async(args=[run_id], queue="orfs_jobs")

except ImportError:
    # Running in backend test context — celery_app not available; skip task registration
    pass
