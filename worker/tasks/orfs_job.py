"""ORFS job execution task stub — implemented in plan 01-03."""
from worker.celery_app import app


@app.task(name="worker.tasks.orfs_job.run_orfs_job", queue="orfs_jobs")
def run_orfs_job(run_id: str) -> None:
    """Execute an ORFS flow job in an isolated Docker container.

    Full implementation in plan 01-03 (job pipeline).
    """
    pass
