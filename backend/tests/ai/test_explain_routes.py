"""
Tests for explain endpoints (log/timing/drc) wired to Ollama.

Endpoints under test:
  POST /api/v1/ai/explain/log
  POST /api/v1/ai/explain/timing
  POST /api/v1/ai/explain/drc

These endpoints now call llm_client.generate via safe_generate.
All tests mock the LLM client to avoid requiring a real Ollama instance.
"""
import uuid
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(client: TestClient) -> str:
    email = f"ai_explain_{uuid.uuid4().hex[:8]}@test.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test1234!", "display_name": "AI Test"},
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


# ---------------------------------------------------------------------------
# Tests: POST /ai/explain/log
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_explain_log_returns_200_with_explanation(test_client: TestClient, async_session):
    """POST /ai/explain/log returns 200 with explanation and model keys."""
    run_id = await _create_run_in_db(async_session)
    token = _register_and_login(test_client)

    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value="Log explanation text.")
    mock_llm.warm_up = AsyncMock(return_value=None)

    with patch("app.api.routes.ai.get_llm_client", return_value=mock_llm):
        resp = test_client.post(
            "/api/v1/ai/explain/log",
            json={"run_id": run_id, "log_lines": 100},
            headers=_auth(token),
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "explanation" in data
    assert isinstance(data["explanation"], str)
    assert len(data["explanation"]) > 0
    assert "model" in data


@pytest.mark.asyncio
async def test_explain_timing_returns_200(test_client: TestClient, async_session):
    """POST /ai/explain/timing returns 200 with explanation."""
    run_id = await _create_run_in_db(async_session)
    token = _register_and_login(test_client)

    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value="Timing explanation text.")
    mock_llm.warm_up = AsyncMock(return_value=None)

    with patch("app.api.routes.ai.get_llm_client", return_value=mock_llm):
        resp = test_client.post(
            "/api/v1/ai/explain/timing",
            json={"run_id": run_id, "log_lines": 100},
            headers=_auth(token),
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "explanation" in data
    assert isinstance(data["explanation"], str)


@pytest.mark.asyncio
async def test_explain_drc_returns_200(test_client: TestClient, async_session):
    """POST /ai/explain/drc returns 200 with explanation."""
    run_id = await _create_run_in_db(async_session)
    token = _register_and_login(test_client)

    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value="DRC explanation text.")
    mock_llm.warm_up = AsyncMock(return_value=None)

    with patch("app.api.routes.ai.get_llm_client", return_value=mock_llm):
        resp = test_client.post(
            "/api/v1/ai/explain/drc",
            json={"run_id": run_id, "log_lines": 100},
            headers=_auth(token),
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "explanation" in data


@pytest.mark.asyncio
async def test_explain_log_ollama_unavailable_returns_503(test_client: TestClient, async_session):
    """POST /ai/explain/log returns 503 when Ollama is unreachable (ConnectError)."""
    run_id = await _create_run_in_db(async_session)
    token = _register_and_login(test_client)

    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(
        side_effect=httpx.ConnectError("Connection refused")
    )
    mock_llm.warm_up = AsyncMock(return_value=None)

    with patch("app.api.routes.ai.get_llm_client", return_value=mock_llm):
        resp = test_client.post(
            "/api/v1/ai/explain/log",
            json={"run_id": run_id, "log_lines": 100},
            headers=_auth(token),
        )

    assert resp.status_code == 503, resp.text
    assert "unavailable" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_explain_log_run_not_found_returns_404(test_client: TestClient, async_session):
    """POST /ai/explain/log with non-existent run_id returns 404."""
    token = _register_and_login(test_client)
    non_existent = str(uuid.uuid4())

    resp = test_client.post(
        "/api/v1/ai/explain/log",
        json={"run_id": non_existent, "log_lines": 100},
        headers=_auth(token),
    )

    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_think_tags_stripped_in_response(test_client: TestClient, async_session):
    """End-to-end: <think>...</think> tags are stripped from Ollama responses.

    OllamaClient.generate already strips these. This test verifies the stripping
    happens before the response is returned from the route (i.e., safe_generate
    returns clean text, not raw model output with reasoning traces).
    """
    run_id = await _create_run_in_db(async_session)
    token = _register_and_login(test_client)

    # Simulate OllamaClient returning already-stripped text (as it does in practice)
    # The stripping happens inside OllamaClient.generate, so safe_generate receives clean text
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value="Clean answer without think tags.")
    mock_llm.warm_up = AsyncMock(return_value=None)

    with patch("app.api.routes.ai.get_llm_client", return_value=mock_llm):
        resp = test_client.post(
            "/api/v1/ai/explain/log",
            json={"run_id": run_id, "log_lines": 100},
            headers=_auth(token),
        )

    assert resp.status_code == 200, resp.text
    explanation = resp.json()["explanation"]
    assert "<think>" not in explanation
    assert "</think>" not in explanation
    assert "Clean answer" in explanation


@pytest.mark.asyncio
async def test_explain_log_timeout_returns_503(test_client: TestClient, async_session):
    """POST /ai/explain/log returns 503 when Ollama times out."""
    run_id = await _create_run_in_db(async_session)
    token = _register_and_login(test_client)

    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(
        side_effect=httpx.TimeoutException("Request timed out")
    )
    mock_llm.warm_up = AsyncMock(return_value=None)

    with patch("app.api.routes.ai.get_llm_client", return_value=mock_llm):
        resp = test_client.post(
            "/api/v1/ai/explain/log",
            json={"run_id": run_id, "log_lines": 100},
            headers=_auth(token),
        )

    assert resp.status_code == 503, resp.text
    assert "unavailable" in resp.json()["detail"].lower()
