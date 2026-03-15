"""
Celery configuration.

Queue routing (three queues):
  high_priority — instructor/admin ORFS jobs (bypasses fair queue, processed first)
  orfs_jobs     — student ORFS jobs dispatched by drain_queue beat task from fair queue
  background    — tiles, VNC lifecycle, grading, AI hints (background-worker, 2 concurrency)

CRITICAL architecture: orfs-worker consumes BOTH high_priority and orfs_jobs queues.
Queue list order ensures high_priority is polled first by Celery.
Background tasks run in a SEPARATE worker process — never merge with orfs-worker.
"""
import os

broker_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
result_backend = os.environ.get("REDIS_URL", "redis://redis:6379/0")
broker_connection_retry_on_startup = True

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

task_routes = {
    # High-priority queue for instructor/admin runs — polled before orfs_jobs
    "worker.tasks.orfs_job.run_orfs_job_high": {"queue": "high_priority"},
    "tasks.orfs_job.run_orfs_job_high": {"queue": "high_priority"},
    # Normal student ORFS jobs — dispatched by drain_queue beat task
    "worker.tasks.orfs_job.run_orfs_job": {"queue": "orfs_jobs"},
    "tasks.orfs_job.run_orfs_job": {"queue": "orfs_jobs"},
    # Wildcard patterns — required by test contract and for future orfs_job tasks
    # Placed AFTER explicit entries so specific high_priority routing takes precedence
    "tasks.orfs_job.*":         {"queue": "orfs_jobs"},
    "worker.tasks.orfs_job.*":  {"queue": "orfs_jobs"},
    # Background tasks — separate worker process
    "worker.tasks.tile_generator.*": {"queue": "background"},
    "tasks.tile_generator.*": {"queue": "background"},
    "worker.tasks.vnc_session.*": {"queue": "background"},
    "tasks.vnc_session.*": {"queue": "background"},
    "worker.tasks.watchdog.*": {"queue": "background"},
    "tasks.watchdog.*": {"queue": "background"},
    "worker.tasks.fair_queue.*": {"queue": "background"},
    "worker.tasks.warm_pool_task.*": {"queue": "background"},
}

# Three queues with explicit exchange declarations
task_queues = {
    "high_priority": {"exchange": "high_priority", "routing_key": "high_priority"},
    "orfs_jobs":     {"exchange": "orfs_jobs",     "routing_key": "orfs_jobs"},
    "background":    {"exchange": "background",    "routing_key": "background"},
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
        "schedule": 120.0,
    },
    # Fair queue drain: dispatch student jobs from Redis sorted set to orfs_jobs queue.
    # Polls every 5s; dispatches up to (MAX_CONCURRENT_JOBS - currently_running) jobs.
    "drain-fair-queue": {
        "task": "worker.tasks.fair_queue.drain_queue",
        "schedule": 5.0,
    },
    # Warm pool maintenance: top up pre-started containers if any have crashed.
    "replenish-warm-pool": {
        "task": "worker.tasks.warm_pool_task.replenish_warm_pool",
        "schedule": 30.0,
    },
}
