"""Celery client for the backend service.

The backend and worker run in separate Docker containers; the backend cannot
import worker task modules directly.  Use send_task() with the registered
task name string to dispatch work to the worker containers.
"""
import os

from celery import Celery

# Minimal Celery app — broker only, no task code loaded.
# REDIS_URL may not be available at import time in tests, so read from env directly.
celery_app = Celery(
    "chipatelier-client",
    broker=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
)

# Configure task routing to match worker queues
celery_app.conf.task_routes = {
    "tasks.orfs_job.*": {"queue": "orfs_jobs"},
    "tasks.tile_generator.*": {"queue": "background"},
    "tasks.vnc_session.*": {"queue": "background"},
    "tasks.watchdog.*": {"queue": "background"},
}
