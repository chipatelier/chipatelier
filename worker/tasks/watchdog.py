"""Orphaned container watchdog Celery beat task.

Runs every 2 minutes (configured in celeryconfig.py beat_schedule).
Finds ORFS containers (named orfs_job_*) whose corresponding run is no longer
in an active state (queued | starting | running) and stops them.

This handles the edge case where:
  - A worker crashes before the finally block runs
  - A container was left running after a Celery worker restart
  - A run was cancelled but the container survived SIGTERM
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from celery_app import app
from container.manager import ContainerManager

# Active statuses — runs in these states are still expected to have a container
_ACTIVE_STATUSES = {"queued", "starting", "running"}


@app.task(
    name="tasks.watchdog.cleanup_orphaned_containers",
    queue="background",
)
def cleanup_orphaned_containers() -> dict:
    """Stop orphaned ORFS containers whose runs are no longer active.

    Returns a summary dict: {"inspected": N, "stopped": N, "errors": N}
    """
    from config import get_settings

    settings = get_settings()
    sync_db_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://", "postgresql://"
    ).replace("sqlite+aiosqlite://", "sqlite://")
    engine = create_engine(sync_db_url)

    manager = ContainerManager()
    containers = manager.list_orfs_containers()

    inspected = 0
    stopped = 0
    errors = 0

    for container_info in containers:
        run_id = container_info["run_id"]
        inspected += 1

        try:
            with Session(engine) as db:
                row = db.execute(
                    text("SELECT status FROM runs WHERE id = :id"),
                    {"id": run_id},
                ).first()

            # Stop if run doesn't exist or is in a terminal state
            if row is None or row.status not in _ACTIVE_STATUSES:
                manager.stop_and_remove(container_info["name"])
                stopped += 1
        except Exception:
            errors += 1

    return {"inspected": inspected, "stopped": stopped, "errors": errors}
