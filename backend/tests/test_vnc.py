"""Wave 0 stub: VNC session tests — implemented in plan 01-06."""
import pytest


async def test_start_vnc_session(test_client, async_session, mock_docker):
    """POST /api/v1/vnc/start/{runId} starts a VNC container and returns token."""
    pass


async def test_vnc_token_is_scoped(test_client, async_session):
    """VNC token is scoped to specific run and user, signed with VNC_TOKEN_SECRET."""
    pass


async def test_stop_vnc_session(test_client, async_session, mock_docker):
    """DELETE /api/v1/vnc/{sessionId} stops and removes VNC container."""
    pass


async def test_vnc_session_limit_enforced(test_client, async_session):
    """MAX_VNC_SESSIONS limit is enforced per deployment."""
    pass
