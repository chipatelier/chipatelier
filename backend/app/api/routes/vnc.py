"""VNC session endpoints.

Routes:
    POST   /vnc/start/{run_id}          — Start a VNC viewer session
    GET    /vnc/validate                — Nginx auth_request validation endpoint
    DELETE /vnc/{session_id}            — Stop a VNC session
"""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_vnc_token, decode_token
from app.models.project import Project
from app.models.run import Run
from app.models.user import User
from app.models.vnc_session import VncSession
from app.schemas.vnc import VncStartResponse, VncSessionResponse

router = APIRouter(prefix="/vnc", tags=["vnc"])

# Base port range for VNC sessions (websockify/noVNC)
_VNC_PORT_BASE = 6080
_VNC_PORT_MAX = 6099


async def _find_available_port(db: AsyncSession) -> int:
    """Find an available port in the VNC port range."""
    used_result = await db.execute(
        select(VncSession.port).where(VncSession.status.in_(["starting", "running"]))
    )
    used_ports = {row[0] for row in used_result.fetchall() if row[0] is not None}

    for port in range(_VNC_PORT_BASE, _VNC_PORT_MAX + 1):
        if port not in used_ports:
            return port

    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="No VNC ports available — all sessions are in use",
    )


# ---------------------------------------------------------------------------
# POST /vnc/start/{run_id} — Start a VNC session
# ---------------------------------------------------------------------------


@router.post(
    "/start/{run_id}",
    response_model=VncStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_vnc_session(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VncStartResponse:
    """Start a VNC viewer session for a completed run.

    Spawns a noVNC container with the run's DEF pre-loaded in OpenROAD GUI.
    Returns an HMAC-signed JWT token (VNC_TOKEN_SECRET) to proxy through Nginx.

    Raises:
        400: Run not found, not owned by user, not complete, or has no artifacts.
        429: MAX_VNC_SESSIONS active sessions reached.
    """
    settings = get_settings()

    # Fetch run and verify ownership via project
    run: Run | None = await db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Run not found")

    project: Project | None = await db.get(Project, run.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Run not found")

    # Verify run is complete
    if run.status != "complete":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="VNC viewer only available for completed runs",
        )

    # Verify artifacts are present
    if not run.artifact_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Run artifacts not yet available",
        )

    # Check global VNC session limit first
    count_result = await db.execute(
        select(func.count(VncSession.id)).where(VncSession.status.in_(["starting", "running"]))
    )
    active_count = count_result.scalar_one()
    if active_count >= settings.MAX_VNC_SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="VNC session limit reached — please try again later",
        )

    # Idempotent: if user already has a running session for this run, return it
    existing_result = await db.execute(
        select(VncSession).where(
            VncSession.user_id == user.id,
            VncSession.run_id == run_id,
            VncSession.status == "running",
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing and existing.token:
        expires_at = existing.expires_at or datetime.now(timezone.utc) + timedelta(hours=2)
        return VncStartResponse(
            session_id=existing.id,
            token=existing.token,
            vnc_url=f"/vnc/{existing.token}",
            expires_at=expires_at,
        )

    # Find available port
    port = await _find_available_port(db)

    # Create session record
    expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
    vnc_session = VncSession(
        user_id=user.id,
        run_id=run_id,
        port=port,
        status="starting",
        expires_at=expires_at,
    )
    db.add(vnc_session)
    await db.commit()
    await db.refresh(vnc_session)

    # Dispatch via send_task — backend and worker run in separate containers
    from app.core.celery_client import celery_app as _celery

    _celery.send_task("tasks.vnc_session.start_vnc", args=[str(vnc_session.id)])

    # Generate HMAC-signed VNC token (VNC_TOKEN_SECRET, NOT JWT_SECRET_KEY)
    token = create_vnc_token(str(user.id), str(run_id), port)

    # Persist token on session record
    vnc_session.token = token
    await db.commit()

    return VncStartResponse(
        session_id=vnc_session.id,
        token=token,
        vnc_url=f"/vnc/{token}",
        expires_at=expires_at,
    )


# ---------------------------------------------------------------------------
# GET /vnc/validate — Nginx auth_request validation (no user Bearer required)
# ---------------------------------------------------------------------------


@router.get("/validate", status_code=status.HTTP_200_OK)
async def validate_vnc_token(
    response: Response,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Validate a VNC session token for Nginx auth_request.

    Called by Nginx before proxying WebSocket traffic to the VNC container.
    Does NOT require a user Bearer token — Nginx calls this endpoint.

    Returns 200 + X-VNC-Port header on success.
    Returns 401 on invalid or expired token.
    """
    settings = get_settings()

    try:
        payload = decode_token(token, secret=settings.VNC_TOKEN_SECRET)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid VNC token")

    if payload.get("type") != "vnc":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid VNC token type")

    port = payload.get("port")
    if port is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing port in VNC token")

    # Verify a running session with this token exists
    session_result = await db.execute(
        select(VncSession).where(
            VncSession.token == token,
            VncSession.status == "running",
        )
    )
    vnc_session = session_result.scalar_one_or_none()
    if not vnc_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="VNC session not active")

    # Return port in header for Nginx to use in proxy_pass
    response.headers["X-VNC-Port"] = str(port)
    return {"status": "ok", "port": port}


# ---------------------------------------------------------------------------
# DELETE /vnc/{session_id} — Stop a VNC session
# ---------------------------------------------------------------------------


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def stop_vnc_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Stop a VNC session and its associated container.

    Raises:
        404: Session not found.
        403: Session does not belong to the current user.
    """
    vnc_session: VncSession | None = await db.get(VncSession, session_id)
    if not vnc_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VNC session not found")

    if vnc_session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    # Stop Docker container if one was spawned
    if vnc_session.container_id:
        try:
            import docker  # noqa: PLC0415

            client = docker.from_env()
            container = client.containers.get(vnc_session.container_id)
            container.stop()
        except Exception:
            # Log but don't fail — container may already be stopped
            pass

    vnc_session.status = "stopped"
    await db.commit()
