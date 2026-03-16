"""
Tests for POST /ai/chat endpoint (Plan 03 — NDJSON streaming).

Covers:
  - test_chat_returns_streaming_response
  - test_chat_history_capped_at_10_turns
  - test_chat_run_not_found_returns_404
  - test_chat_requires_auth
  - test_chat_x_accel_buffering_header
"""
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(client: TestClient) -> str:
    email = f"ai_chat_{uuid.uuid4().hex[:8]}@test.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test1234!", "display_name": "Chat Test"},
    )
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Test1234!"})
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_run_in_db(async_session, ppa=None, config=None) -> str:
    """Create a user + project + run in the test DB; return run UUID as str."""
    from app.models.user import User
    from app.models.project import Project
    from app.models.run import Run

    user = User(
        email=f"runner_{uuid.uuid4().hex[:8]}@test.com",
        display_name="Run Owner",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$test",
        is_active=True,
        role="student",
    )
    async_session.add(user)
    await async_session.flush()

    project = Project(user_id=user.id, name="Test Project", pdk="sky130hd")
    async_session.add(project)
    await async_session.flush()

    run = Run(
        project_id=project.id,
        status="complete",
        stage_completed="route",
        target_stage="finish",
        ppa=ppa if ppa is not None else {
            "worst_negative_slack": -0.05,
            "total_negative_slack": -1.0,
            "drc_routing_errors": 0,
        },
        config=config if config is not None else {
            "DESIGN_NAME": "gcd",
            "PLATFORM": "sky130hd",
            "CLOCK_PERIOD": "10",
            "CORE_UTILIZATION": "40",
        },
    )
    async_session.add(run)
    await async_session.commit()
    return str(run.id)


def _make_mock_llm(tokens=("Hello", " world")):
    """Return a mock LLM client whose chat_stream yields the given tokens."""
    mock_llm = AsyncMock()
    mock_llm.warm_up = AsyncMock(return_value=None)

    async def _stream(*args, **kwargs):
        for t in tokens:
            yield {"message": {"content": t}}

    mock_llm.chat_stream = AsyncMock(side_effect=_stream)
    return mock_llm


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_returns_streaming_response(test_client: TestClient, async_session):
    """POST /ai/chat returns 200 with NDJSON content-type and valid token stream."""
    run_id = await _create_run_in_db(async_session)
    token = _register_and_login(test_client)
    mock_llm = _make_mock_llm(("Hello", " world"))

    with patch("app.api.routes.ai.get_llm_client", return_value=mock_llm):
        resp = test_client.post(
            "/api/v1/ai/chat",
            json={"run_id": run_id, "message": "What is WNS?", "history": []},
            headers=_auth(token),
        )

    assert resp.status_code == 200, resp.text
    assert "application/x-ndjson" in resp.headers.get("content-type", "")

    lines = [ln for ln in resp.text.strip().split("\n") if ln.strip()]
    parsed = [json.loads(ln) for ln in lines]

    # At least one token line
    token_lines = [p for p in parsed if "token" in p]
    assert len(token_lines) >= 1, f"No token lines found: {parsed}"

    # Last line must be done
    assert parsed[-1] == {"done": True}, f"Last line not done: {parsed[-1]}"


@pytest.mark.asyncio
async def test_chat_history_capped_at_10_turns(test_client: TestClient, async_session):
    """POST /ai/chat with 30-message history — only last 20 messages forwarded to LLM."""
    run_id = await _create_run_in_db(async_session)
    token = _register_and_login(test_client)

    captured_messages: list = []

    async def _capture_stream(messages, **kwargs):
        captured_messages.extend(messages)
        yield {"message": {"content": "ok"}}

    mock_llm = AsyncMock()
    mock_llm.warm_up = AsyncMock(return_value=None)
    mock_llm.chat_stream = AsyncMock(side_effect=_capture_stream)

    # 30 history messages (15 turns)
    big_history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
        for i in range(30)
    ]

    with patch("app.api.routes.ai.get_llm_client", return_value=mock_llm):
        resp = test_client.post(
            "/api/v1/ai/chat",
            json={"run_id": run_id, "message": "final question", "history": big_history},
            headers=_auth(token),
        )

    assert resp.status_code == 200, resp.text

    # system(1) + last 20 history + 1 user = 22 total (NOT 32)
    assert len(captured_messages) == 22, (
        f"Expected 22 messages (system+20 history+user), got {len(captured_messages)}"
    )
    assert captured_messages[0]["role"] == "system"
    assert captured_messages[-1]["content"] == "final question"


@pytest.mark.asyncio
async def test_chat_run_not_found_returns_404(test_client: TestClient, async_session):
    """POST /ai/chat with non-existent run_id returns 404."""
    token = _register_and_login(test_client)
    mock_llm = _make_mock_llm()

    with patch("app.api.routes.ai.get_llm_client", return_value=mock_llm):
        resp = test_client.post(
            "/api/v1/ai/chat",
            json={"run_id": str(uuid.uuid4()), "message": "hello", "history": []},
            headers=_auth(token),
        )

    assert resp.status_code == 404, resp.text


def test_chat_requires_auth(test_client: TestClient):
    """POST /ai/chat without auth header returns 401."""
    resp = test_client.post(
        "/api/v1/ai/chat",
        json={"run_id": str(uuid.uuid4()), "message": "hello", "history": []},
    )
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_chat_x_accel_buffering_header(test_client: TestClient, async_session):
    """POST /ai/chat response includes X-Accel-Buffering: no header."""
    run_id = await _create_run_in_db(async_session)
    token = _register_and_login(test_client)
    mock_llm = _make_mock_llm(("hi",))

    with patch("app.api.routes.ai.get_llm_client", return_value=mock_llm):
        resp = test_client.post(
            "/api/v1/ai/chat",
            json={"run_id": run_id, "message": "hi", "history": []},
            headers=_auth(token),
        )

    assert resp.status_code == 200, resp.text
    assert resp.headers.get("x-accel-buffering", "").lower() == "no"
