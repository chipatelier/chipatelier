"""
Integration-style tests for chat NDJSON streaming behavior.

Covers:
  - test_stream_yields_ndjson_tokens
  - test_stream_strips_think_tags
  - test_stream_handles_ollama_error
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
    email = f"ai_stream_{uuid.uuid4().hex[:8]}@test.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test1234!", "display_name": "Stream Test"},
    )
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Test1234!"})
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_run_in_db(async_session) -> str:
    """Create a user + project + run; return run UUID as str."""
    from app.models.user import User
    from app.models.project import Project
    from app.models.run import Run

    user = User(
        email=f"stream_{uuid.uuid4().hex[:8]}@test.com",
        display_name="Stream Owner",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$test",
        is_active=True,
        role="student",
    )
    async_session.add(user)
    await async_session.flush()

    project = Project(user_id=user.id, name="Stream Project", pdk="sky130hd")
    async_session.add(project)
    await async_session.flush()

    run = Run(
        project_id=project.id,
        status="complete",
        stage_completed="route",
        target_stage="finish",
        ppa={"worst_negative_slack": 3.88, "drc_routing_errors": 0},
        config={"DESIGN_NAME": "gcd", "PLATFORM": "sky130hd"},
    )
    async_session.add(run)
    await async_session.commit()
    return str(run.id)


def _post_chat(client: TestClient, run_id: str, token: str, message: str = "Test?"):
    return client.post(
        "/api/v1/ai/chat",
        json={"run_id": run_id, "message": message, "history": []},
        headers=_auth(token),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stream_yields_ndjson_tokens(test_client: TestClient, async_session):
    """Mock chat_stream yields 3 tokens — response body has 3 token lines + 1 done line."""
    run_id = await _create_run_in_db(async_session)
    token = _register_and_login(test_client)

    async def _three_tokens(*args, **kwargs):
        yield {"message": {"content": "Hello"}}
        yield {"message": {"content": " "}}
        yield {"message": {"content": "world"}}

    mock_llm = AsyncMock()
    mock_llm.warm_up = AsyncMock(return_value=None)
    mock_llm.chat_stream = AsyncMock(side_effect=_three_tokens)

    with patch("app.api.routes.ai.get_llm_client", return_value=mock_llm):
        resp = _post_chat(test_client, run_id, token, "Say hello world")

    assert resp.status_code == 200, resp.text
    lines = [ln for ln in resp.text.strip().split("\n") if ln.strip()]
    parsed = [json.loads(ln) for ln in lines]

    token_lines = [p for p in parsed if "token" in p]
    done_lines = [p for p in parsed if "done" in p]

    assert len(token_lines) == 3, f"Expected 3 token lines, got {token_lines}"
    assert token_lines[0]["token"] == "Hello"
    assert token_lines[1]["token"] == " "
    assert token_lines[2]["token"] == "world"
    assert len(done_lines) == 1
    assert done_lines[0] == {"done": True}


@pytest.mark.asyncio
async def test_stream_strips_think_tags(test_client: TestClient, async_session):
    """Tokens containing <think>...</think> are stripped from the output."""
    run_id = await _create_run_in_db(async_session)
    token = _register_and_login(test_client)

    async def _think_tokens(*args, **kwargs):
        # Simulate deepseek-r1 reasoning block followed by actual answer
        yield {"message": {"content": "<think>"}}
        yield {"message": {"content": "internal reasoning"}}
        yield {"message": {"content": "</think>"}}
        yield {"message": {"content": "\nAnswer"}}

    mock_llm = AsyncMock()
    mock_llm.warm_up = AsyncMock(return_value=None)
    mock_llm.chat_stream = AsyncMock(side_effect=_think_tokens)

    with patch("app.api.routes.ai.get_llm_client", return_value=mock_llm):
        resp = _post_chat(test_client, run_id, token, "Explain")

    assert resp.status_code == 200, resp.text
    lines = [ln for ln in resp.text.strip().split("\n") if ln.strip()]
    parsed = [json.loads(ln) for ln in lines]

    token_lines = [p for p in parsed if "token" in p]
    full_text = "".join(p["token"] for p in token_lines)

    # <think> content must not appear in any token line
    assert "<think>" not in full_text, f"<think> found in output: {full_text!r}"
    assert "internal reasoning" not in full_text, f"Reasoning leaked: {full_text!r}"
    # The actual answer should be present
    assert "Answer" in full_text, f"Answer missing from output: {full_text!r}"


@pytest.mark.asyncio
async def test_stream_handles_ollama_error(test_client: TestClient, async_session):
    """When chat_stream raises, response body contains an error JSON line."""
    run_id = await _create_run_in_db(async_session)
    token = _register_and_login(test_client)

    async def _error_stream(*args, **kwargs):
        raise RuntimeError("Ollama crashed")
        yield  # make it a generator

    mock_llm = AsyncMock()
    mock_llm.warm_up = AsyncMock(return_value=None)
    mock_llm.chat_stream = AsyncMock(side_effect=_error_stream)

    with patch("app.api.routes.ai.get_llm_client", return_value=mock_llm):
        resp = _post_chat(test_client, run_id, token, "What happened?")

    # Response is still 200 (streaming already started); body has error line
    assert resp.status_code == 200, resp.text
    lines = [ln for ln in resp.text.strip().split("\n") if ln.strip()]
    parsed = [json.loads(ln) for ln in lines]

    error_lines = [p for p in parsed if "error" in p]
    assert len(error_lines) >= 1, f"No error line in stream: {parsed}"
    assert "unavailable" in error_lines[0]["error"].lower()
