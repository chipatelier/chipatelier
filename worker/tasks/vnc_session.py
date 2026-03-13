"""VNC session lifecycle task — spawns noVNC containers with DEF pre-loaded."""
import logging

from worker.celery_app import app

logger = logging.getLogger(__name__)


def start_vnc_container(session_id: str, artifact_path: str, port: int) -> str:
    """Spawn a noVNC container for interactive OpenROAD viewing.

    The container uses chipatelier/vnc-viewer image with:
      - Xvfb + x11vnc + websockify managed by supervisord
      - OpenROAD GUI pre-loaded with the student's DEF file

    Args:
        session_id: VncSession.id (string UUID) — used to name the container.
        artifact_path: MinIO artifact prefix, e.g. "runs/{run_id}/". The DEF
            file is expected at {artifact_path}6_final.def.
        port: Host port to bind websockify on (6080–6099 range).

    Returns:
        container_id: Docker container ID string.
    """
    import docker  # noqa: PLC0415

    def_path = f"/artifacts/{artifact_path}6_final.def"
    lef_path = f"/artifacts/{artifact_path}merged.lef"

    client = docker.from_env()
    container = client.containers.run(
        image="chipatelier/vnc-viewer:latest",
        name=f"vnc_session_{session_id}",
        detach=True,
        ports={6080: port},  # websockify port → host port
        environment={
            "VNC_DEF_PATH": def_path,
            "VNC_LEF_PATH": lef_path,
            "DISPLAY": ":99",
        },
        # VNC containers need display access — NOT read-only
        # Network must be accessible so websockify can accept connections from Nginx
    )
    logger.info("VNC container started: %s for session %s on port %d", container.id, session_id, port)
    return container.id


@app.task(name="worker.tasks.vnc_session.start_vnc", queue="background")
def start_vnc(session_id: str) -> None:
    """Celery task: start a VNC session container for interactive OpenROAD viewing.

    Fetches the VncSession from the database, spawns the container via Docker SDK,
    and updates the session record with container_id and status="running".
    """
    import os
    import sys

    # Ensure backend is importable from worker context
    _project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.config import get_settings

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _run():
        from uuid import UUID

        from app.models.vnc_session import VncSession

        async with session_factory() as db:
            vnc_session = await db.get(VncSession, UUID(session_id))
            if not vnc_session:
                logger.error("VncSession %s not found", session_id)
                return

            artifact_path = None
            # Get artifact_path from the associated run
            from app.models.run import Run

            run = await db.get(Run, vnc_session.run_id)
            if run and run.artifact_path:
                artifact_path = run.artifact_path

            if not artifact_path:
                logger.error("No artifact_path for run %s, cannot start VNC", vnc_session.run_id)
                vnc_session.status = "stopped"
                await db.commit()
                return

            port = vnc_session.port or 6080

            try:
                container_id = start_vnc_container(
                    session_id=session_id,
                    artifact_path=artifact_path,
                    port=port,
                )
                vnc_session.container_id = container_id
                vnc_session.status = "running"
                await db.commit()
                logger.info("VNC session %s running on port %d", session_id, port)
            except Exception as exc:
                logger.error("Failed to start VNC container for session %s: %s", session_id, exc)
                vnc_session.status = "stopped"
                await db.commit()

    asyncio.run(_run())
