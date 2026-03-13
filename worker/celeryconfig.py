"""
Celery configuration.

Queue routing:
  orfs_jobs  — long-running ORFS container jobs (orfs-worker, 4 concurrency)
  background — tiles, VNC lifecycle, grading, AI hints (background-worker, 2 concurrency)

CRITICAL architecture: These are TWO SEPARATE worker processes.
Do not merge into one worker with -Q orfs_jobs,background.
"""
import os

broker_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
result_backend = os.environ.get("REDIS_URL", "redis://redis:6379/0")

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

task_routes = {
    "worker.tasks.orfs_job.*": {"queue": "orfs_jobs"},
    "worker.tasks.tile_generator.*": {"queue": "background"},
    "worker.tasks.vnc_session.*": {"queue": "background"},
    "worker.tasks.watchdog.*": {"queue": "background"},
}

task_queues = {
    "orfs_jobs": {"exchange": "orfs_jobs", "routing_key": "orfs_jobs"},
    "background": {"exchange": "background", "routing_key": "background"},
}

# Prevent ORFS tasks from being prefetched — they are long-running
worker_prefetch_multiplier = 1

# Re-queue task on worker crash (safe for idempotent tasks)
task_acks_late = True

# ---------------------------------------------------------------------------
# Celery Beat schedule — periodic tasks
# ---------------------------------------------------------------------------
beat_schedule = {
    # Orphaned container watchdog: stop containers whose runs are no longer active.
    # Runs every 2 minutes. Handles worker crash / SIGTERM-survived containers.
    "cleanup-orphaned-containers": {
        "task": "worker.tasks.watchdog.cleanup_orphaned_containers",
        "schedule": 120.0,  # every 2 minutes
    },
}
