"""VNC session lifecycle task stub — implemented in plan 01-06."""
from worker.celery_app import app


@app.task(name="worker.tasks.vnc_session.start_vnc", queue="background")
def start_vnc(session_id: str) -> None:
    """Start a VNC session container for interactive OpenROAD viewing.

    Full implementation in plan 01-06 (VNC viewer).
    """
    pass
