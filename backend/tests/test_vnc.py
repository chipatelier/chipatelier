"""LAYT-01 tests: VNC session API — token creation, session management, container lifecycle."""
import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VNC_SECRET = "test-vnc-secret-for-testing"

os.environ.setdefault("VNC_TOKEN_SECRET", VNC_SECRET)


def _make_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_access_token(user_id: str) -> str:
    """Create a short-lived access token using the test JWT_SECRET_KEY."""
    from app.core.security import create_access_token
    return create_access_token(user_id)


# ---------------------------------------------------------------------------
# Test: create_vnc_token uses VNC_TOKEN_SECRET (not JWT_SECRET_KEY)
# ---------------------------------------------------------------------------

def test_vnc_token_creation():
    """VNC token is signed with VNC_TOKEN_SECRET and contains expected payload."""
    from app.core.security import create_vnc_token

    user_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    port = 6080

    token = create_vnc_token(user_id, run_id, port)

    # Must decode successfully with VNC_TOKEN_SECRET
    payload = jwt.decode(token, VNC_SECRET, algorithms=["HS256"])

    assert payload["type"] == "vnc"
    assert payload["run_id"] == run_id
    assert payload["port"] == port
    assert payload["sub"] == user_id

    # Must NOT decode with JWT_SECRET_KEY
    jwt_secret = os.environ.get("JWT_SECRET_KEY", "test-secret-key-for-testing")
    with pytest.raises((jwt.InvalidSignatureError, jwt.DecodeError)):
        jwt.decode(token, jwt_secret, algorithms=["HS256"])


# ---------------------------------------------------------------------------
# Test: GET /api/v1/vnc/validate - valid token returns 200 + X-VNC-Port header
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vnc_validate_valid(test_client, async_session):
    """GET /vnc/validate?token={valid_vnc_token} returns 200 and X-VNC-Port header."""
    from app.core.security import create_vnc_token
    from app.models.vnc_session import VncSession
    from app.models.user import User

    user = User(
        email="vnc_valid@test.com",
        display_name="VNC Valid",
        password_hash="hash",
        role="student",
        is_active=True,
        storage_used_bytes=0,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    run_id = str(uuid.uuid4())
    port = 6080

    token = create_vnc_token(str(user.id), run_id, port)

    # Create a VncSession in DB with status="running" and this token
    session_record = VncSession(
        user_id=user.id,
        run_id=uuid.UUID(run_id),
        status="running",
        token=token,
        port=port,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
    )
    async_session.add(session_record)
    await async_session.commit()

    resp = test_client.get(f"/api/v1/vnc/validate?token={token}")
    assert resp.status_code == 200
    assert resp.headers.get("x-vnc-port") == str(port)


@pytest.mark.asyncio
async def test_vnc_validate_invalid(test_client):
    """GET /vnc/validate?token=garbage returns 401."""
    resp = test_client.get("/api/v1/vnc/validate?token=totally-invalid-garbage")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Test: POST /api/v1/vnc/start/{run_id} - happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vnc_start_endpoint(test_client, async_session, mock_docker):
    """POST /vnc/start/{runId} with a completed run returns 201 with session_id and token."""
    from app.models.user import User
    from app.models.project import Project
    from app.models.run import Run

    # Create user, project, and a completed run
    user = User(
        email="vnc_start@test.com",
        display_name="VNC Start",
        password_hash="hash",
        role="student",
        is_active=True,
        storage_used_bytes=0,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    project = Project(user_id=user.id, name="Test Project", pdk="sky130hd")
    async_session.add(project)
    await async_session.commit()
    await async_session.refresh(project)

    run = Run(
        project_id=project.id,
        status="complete",
        target_stage="route",
        artifact_path=f"runs/{uuid.uuid4()}/",
    )
    async_session.add(run)
    await async_session.commit()
    await async_session.refresh(run)

    access_token = _make_access_token(str(user.id))

    with patch("app.core.celery_client.celery_app.send_task") as mock_task:
        mock_task.delay = MagicMock(return_value=MagicMock(id="celery-task-id"))
        resp = test_client.post(
            f"/api/v1/vnc/start/{run.id}",
            headers=_make_headers(access_token),
        )

    assert resp.status_code == 201
    data = resp.json()
    assert "session_id" in data
    assert "token" in data
    assert "vnc_url" in data
    assert "expires_at" in data
    # vnc_url must embed the token in the path (not query string)
    assert data["token"] in data["vnc_url"]
    assert data["vnc_url"].startswith("/vnc/")

    # Decode the VNC token — must use VNC_TOKEN_SECRET
    payload = jwt.decode(data["token"], VNC_SECRET, algorithms=["HS256"])
    assert payload["type"] == "vnc"
    assert payload["run_id"] == str(run.id)


# ---------------------------------------------------------------------------
# Test: POST /api/v1/vnc/start/{run_id} - run not complete => 400
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vnc_start_not_complete(test_client, async_session):
    """POST /vnc/start/{runId} with a non-complete run returns 400."""
    from app.models.user import User
    from app.models.project import Project
    from app.models.run import Run

    user = User(
        email="vnc_notcomplete@test.com",
        display_name="VNC NotComplete",
        password_hash="hash",
        role="student",
        is_active=True,
        storage_used_bytes=0,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    project = Project(user_id=user.id, name="Test Project 2", pdk="sky130hd")
    async_session.add(project)
    await async_session.commit()
    await async_session.refresh(project)

    run = Run(
        project_id=project.id,
        status="running",  # Not complete
        target_stage="route",
    )
    async_session.add(run)
    await async_session.commit()
    await async_session.refresh(run)

    access_token = _make_access_token(str(user.id))
    resp = test_client.post(
        f"/api/v1/vnc/start/{run.id}",
        headers=_make_headers(access_token),
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Test: MAX_VNC_SESSIONS limit => 429
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vnc_session_limit(test_client, async_session):
    """If MAX_VNC_SESSIONS running sessions exist, new start returns 429."""
    from app.models.user import User
    from app.models.project import Project
    from app.models.run import Run
    from app.models.vnc_session import VncSession

    user = User(
        email="vnc_limit@test.com",
        display_name="VNC Limit",
        password_hash="hash",
        role="student",
        is_active=True,
        storage_used_bytes=0,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    project = Project(user_id=user.id, name="Limit Project", pdk="sky130hd")
    async_session.add(project)
    await async_session.commit()
    await async_session.refresh(project)

    run = Run(
        project_id=project.id,
        status="complete",
        target_stage="route",
        artifact_path=f"runs/{uuid.uuid4()}/",
    )
    async_session.add(run)
    await async_session.commit()
    await async_session.refresh(run)

    # Create MAX_VNC_SESSIONS (8) running sessions
    for i in range(8):
        s = VncSession(
            user_id=user.id,
            run_id=run.id,
            status="running",
            port=6080 + i,
        )
        async_session.add(s)
    await async_session.commit()

    access_token = _make_access_token(str(user.id))
    resp = test_client.post(
        f"/api/v1/vnc/start/{run.id}",
        headers=_make_headers(access_token),
    )
    assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Test: DELETE /api/v1/vnc/{session_id} - stop session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vnc_cancel(test_client, async_session, mock_docker):
    """DELETE /vnc/{session_id} stops the container and sets status to stopped."""
    from app.models.user import User
    from app.models.project import Project
    from app.models.run import Run
    from app.models.vnc_session import VncSession

    user = User(
        email="vnc_cancel@test.com",
        display_name="VNC Cancel",
        password_hash="hash",
        role="student",
        is_active=True,
        storage_used_bytes=0,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    project = Project(user_id=user.id, name="Cancel Project", pdk="sky130hd")
    async_session.add(project)
    await async_session.commit()
    await async_session.refresh(project)

    run = Run(project_id=project.id, status="complete", target_stage="route")
    async_session.add(run)
    await async_session.commit()
    await async_session.refresh(run)

    vnc_session = VncSession(
        user_id=user.id,
        run_id=run.id,
        container_id="mock-container-id",
        port=6090,
        status="running",
    )
    async_session.add(vnc_session)
    await async_session.commit()
    await async_session.refresh(vnc_session)

    access_token = _make_access_token(str(user.id))
    resp = test_client.delete(
        f"/api/v1/vnc/{vnc_session.id}",
        headers=_make_headers(access_token),
    )
    assert resp.status_code == 204

    # Verify session is stopped in DB
    await async_session.refresh(vnc_session)
    assert vnc_session.status == "stopped"

    # Verify docker stop was called
    mock_docker.return_value.containers.get.assert_called_once_with("mock-container-id")
    mock_docker.return_value.containers.get.return_value.stop.assert_called_once()


# ---------------------------------------------------------------------------
# Test: VNC container spawned with DEF path env var
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vnc_container_def_env_var(test_client, async_session, mock_docker):
    """When VNC session starts, container is spawned with VNC_DEF_PATH env var."""
    from app.models.user import User
    from app.models.project import Project
    from app.models.run import Run

    user = User(
        email="vnc_defenv@test.com",
        display_name="VNC DefEnv",
        password_hash="hash",
        role="student",
        is_active=True,
        storage_used_bytes=0,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    project = Project(user_id=user.id, name="DefEnv Project", pdk="sky130hd")
    async_session.add(project)
    await async_session.commit()
    await async_session.refresh(project)

    run_id_val = uuid.uuid4()
    run = Run(
        id=run_id_val,
        project_id=project.id,
        status="complete",
        target_stage="route",
        artifact_path=f"runs/{run_id_val}/",
    )
    async_session.add(run)
    await async_session.commit()
    await async_session.refresh(run)

    # Call the task directly (synchronous — mocked Docker)
    with patch("docker.from_env") as mock_docker_fn:
        mock_container = MagicMock()
        mock_container.id = "test-container-id"
        mock_docker_fn.return_value.containers.run.return_value = mock_container

        from worker.tasks.vnc_session import start_vnc_container
        vnc_session_id = str(uuid.uuid4())
        artifact_path = f"runs/{run_id_val}/"

        start_vnc_container(
            session_id=vnc_session_id,
            artifact_path=artifact_path,
            port=6085,
        )

        # Verify container was spawned with VNC_DEF_PATH env var
        call_kwargs = mock_docker_fn.return_value.containers.run.call_args
        env = call_kwargs.kwargs.get("environment", {})
        if not env:
            # Try positional
            env = call_kwargs[1].get("environment", {})
        assert "VNC_DEF_PATH" in env
        assert "6_final.def" in env["VNC_DEF_PATH"]
