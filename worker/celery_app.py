"""Celery application instance with worker lifecycle signals."""
from celery import Celery
from celery.signals import worker_ready, worker_shutdown

app = Celery("chipatelier")
app.config_from_object("celeryconfig")
app.autodiscover_tasks(["tasks"])


# ---------------------------------------------------------------------------
# Worker lifecycle signals — warm pool initialization
# ---------------------------------------------------------------------------

@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    """Initialize warm container pool when orfs-worker starts.

    Pre-starts WARM_POOL_SIZE/2 ORFS containers so the first jobs start fast.
    Only runs on the orfs-worker (background-worker has no Docker socket access).
    """
    try:
        from app.core.config import get_settings
        from container.warm_pool import init_warm_pool
        settings = get_settings()
        pool = init_warm_pool(settings)
        # Pre-fill pool to target size
        started = 0
        for _ in range(pool._target_size):
            if pool.replenish():
                started += 1
        print(f"[chipatelier] Warm pool initialized: {started}/{pool._target_size} containers ready")
    except Exception as exc:
        # Non-fatal: worker runs fine without warm pool (cold-start fallback)
        print(f"[chipatelier] Warm pool init skipped: {exc}")


@worker_shutdown.connect
def on_worker_shutdown(sender, **kwargs):
    """Drain warm container pool on graceful shutdown."""
    try:
        from container.warm_pool import get_warm_pool
        pool = get_warm_pool()
        if pool:
            count = pool.drain()
            print(f"[chipatelier] Warm pool drained: {count} containers removed")
    except Exception:
        pass  # Non-fatal on shutdown
