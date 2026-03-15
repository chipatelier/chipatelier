"""Task modules for ChipAtelier workers."""
# Import all task modules so Celery autodiscover can find them
try:
    from tasks import orfs_job  # noqa: F401
    from tasks import tile_generator  # noqa: F401
    from tasks import vnc_session  # noqa: F401
    from tasks import watchdog  # noqa: F401
    from tasks import checkpoint_eval  # noqa: F401
except ImportError:
    # When imported as worker.tasks (project root in sys.path), use absolute imports
    pass
