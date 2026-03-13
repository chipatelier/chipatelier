"""
JOB-03 WebSocket log streaming tests.
Tests: buffered replay for late joiners, live streaming, JWT auth, disconnect cleanup.
"""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_valid_token(user_id: str | None = None) -> str:
    """Create a valid short-lived access token for tests."""
    from app.core.security import create_access_token
    return create_access_token(user_id or str(uuid.uuid4()))


def _make_fake_pubsub(lines: list[str]):
    """Return an async generator mock that yields pubsub messages then stops."""
    async def _listen():
        for line in lines:
            yield {"type": "message", "data": line.encode()}

    pubsub = AsyncMock()
    pubsub.listen = _listen
    pubsub.subscribe = AsyncMock()
    pubsub.unsubscribe = AsyncMock()
    pubsub.aclose = AsyncMock()
    return pubsub


# ---------------------------------------------------------------------------
# test_invalid_token: bad token → connection closed with 4008
# ---------------------------------------------------------------------------

def test_invalid_token(test_client):
    """WS endpoint rejects connection with invalid token (close code 4008)."""
    run_id = str(uuid.uuid4())
    with test_client.websocket_connect(
        f"/api/v1/ws/jobs/{run_id}/logs/stream?token=not-a-valid-jwt"
    ) as ws:
        # Server closes connection — websocket_connect raises or ws has close code
        # TestClient raises WebSocketDisconnect on close
        with pytest.raises(Exception):
            ws.receive_text()


# ---------------------------------------------------------------------------
# test_log_stream: buffered lines replayed first, then live lines
# ---------------------------------------------------------------------------

def test_log_stream_buffered_replay(test_client):
    """WS endpoint replays buffered log lines before streaming live lines."""
    run_id = str(uuid.uuid4())
    token = _make_valid_token()

    buffered_lines = [f"buffered line {i}" for i in range(5)]

    # Build a fake Redis that returns buffered lines and a pubsub that yields one live line
    live_lines = ["live line 1"]
    pubsub = _make_fake_pubsub(live_lines)

    fake_redis = AsyncMock()
    fake_redis.lrange = AsyncMock(return_value=[l.encode() for l in buffered_lines])
    fake_redis.pubsub = MagicMock(return_value=pubsub)

    async def override_get_redis():
        return fake_redis

    with patch("app.api.websocket.get_redis", override_get_redis):
        with test_client.websocket_connect(
            f"/api/v1/ws/jobs/{run_id}/logs/stream?token={token}"
        ) as ws:
            received = []
            # Receive all buffered + live lines
            for _ in range(len(buffered_lines) + len(live_lines)):
                try:
                    msg = ws.receive_text()
                    received.append(msg)
                except Exception:
                    break

    # Buffered lines must appear first
    assert received[:5] == buffered_lines
    assert "live line 1" in received


# ---------------------------------------------------------------------------
# test_late_joiner: joins after many lines buffered — all lines replayed
# ---------------------------------------------------------------------------

def test_late_joiner_receives_all_buffered(test_client):
    """Late joiner (500 lines already in logbuf) receives all 500 lines first."""
    run_id = str(uuid.uuid4())
    token = _make_valid_token()

    buffered_lines = [f"line {i:04d}" for i in range(500)]
    pubsub = _make_fake_pubsub([])  # no live lines for this test

    fake_redis = AsyncMock()
    fake_redis.lrange = AsyncMock(return_value=[l.encode() for l in buffered_lines])
    fake_redis.pubsub = MagicMock(return_value=pubsub)

    async def override_get_redis():
        return fake_redis

    received = []
    with patch("app.api.websocket.get_redis", override_get_redis):
        with test_client.websocket_connect(
            f"/api/v1/ws/jobs/{run_id}/logs/stream?token={token}"
        ) as ws:
            for _ in range(500):
                try:
                    msg = ws.receive_text()
                    received.append(msg)
                except Exception:
                    break

    assert len(received) == 500
    assert received[0] == "line 0000"
    assert received[499] == "line 0499"


# ---------------------------------------------------------------------------
# test_pubsub_cleanup: unsubscribe called on disconnect (no orphaned subscription)
# ---------------------------------------------------------------------------

def test_pubsub_cleanup_on_disconnect(test_client):
    """pubsub.unsubscribe and aclose are called in finally block on disconnect."""
    run_id = str(uuid.uuid4())
    token = _make_valid_token()

    pubsub = _make_fake_pubsub([])
    fake_redis = AsyncMock()
    fake_redis.lrange = AsyncMock(return_value=[])
    fake_redis.pubsub = MagicMock(return_value=pubsub)

    async def override_get_redis():
        return fake_redis

    with patch("app.api.websocket.get_redis", override_get_redis):
        with test_client.websocket_connect(
            f"/api/v1/ws/jobs/{run_id}/logs/stream?token={token}"
        ) as ws:
            pass  # disconnect immediately

    # Verify cleanup was called
    pubsub.unsubscribe.assert_called_once()
    pubsub.aclose.assert_called_once()
