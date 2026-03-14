"""Celery beat task for warm pool maintenance.

Registered in celeryconfig.py beat_schedule as "replenish-warm-pool" (every 30s).
Tops up the pre-started container pool if containers have crashed since last check.

Runs on the background queue — the background-worker process handles this.
"""
from celery_app import app


@app.task(name="worker.tasks.warm_pool_task.replenish_warm_pool", queue="background")
def replenish_warm_pool():
    """Ensure warm pool has at least _target_size containers available.

    Called every 30s by Celery beat. Adds containers until pool reaches target size.
    Non-fatal: if Docker is unavailable, logs and returns.
    """
    try:
        from container.warm_pool import get_warm_pool
        pool = get_warm_pool()
        if pool is None:
            return  # Pool not initialized on this worker (e.g., background-worker)
        pool.replenish()
    except Exception as exc:
        # Non-fatal: warm pool is an optimization, not required for correctness
        print(f"[chipatelier] warm_pool replenish failed: {exc}")
