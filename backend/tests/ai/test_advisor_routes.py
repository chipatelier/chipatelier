"""
Tests for the config advisor endpoint.

Endpoint under test:
  POST /api/v1/ai/advisor/config

This endpoint calls llm_client.generate via safe_generate.
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
    email = f"ai_advisor_{uuid.uuid4().hex[:8]}@test.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test1234!", "display_name": "Advisor Test"},
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
        email=f"advisor_runner_{uuid.uuid4().hex[:8]}@test.com",
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
        ppa=ppa,
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
# Tests: POST /ai/advisor/config
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_advisor_config_returns_200_with_suggestions(test_client: TestClient, async_session):
    """POST /ai/advisor/config returns 200 with suggestions and model keys."""
    run_id = await _create_run_in_db(async_session, ppa={
        "worst_negative_slack": -2.3,
        "drc_routing_errors": 0,
        "core_utilization": 0.40,
    })
    token = _register_and_login(test_client)

    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(
        return_value=(
            "CORE_UTILIZATION: 40 -> 35 | Reason: High utilization causing congestion.\n"
            "CLOCK_PERIOD: 10 -> keep | Reason: Looks good."
        )
    )
    mock_llm.warm_up = AsyncMock(return_value=None)

    with patch("app.api.routes.ai.get_llm_client", return_value=mock_llm):
        resp = test_client.post(
            "/api/v1/ai/advisor/config",
            json={"run_id": run_id},
            headers=_auth(token),
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "suggestions" in data
    assert isinstance(data["suggestions"], str)
    assert len(data["suggestions"]) > 0
    assert "model" in data


@pytest.mark.asyncio
async def test_advisor_config_no_ppa_returns_200(test_client: TestClient, async_session):
    """POST /ai/advisor/config with null ppa returns 200 (general guidance)."""
    run_id = await _create_run_in_db(async_session, ppa=None)
    token = _register_and_login(test_client)

    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(
        return_value="General guidance: Consider reducing CORE_UTILIZATION."
    )
    mock_llm.warm_up = AsyncMock(return_value=None)

    with patch("app.api.routes.ai.get_llm_client", return_value=mock_llm):
        resp = test_client.post(
            "/api/v1/ai/advisor/config",
            json={"run_id": run_id},
            headers=_auth(token),
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "suggestions" in data


@pytest.mark.asyncio
async def test_advisor_config_ollama_unavailable_returns_503(test_client: TestClient, async_session):
    """POST /ai/advisor/config returns 503 when Ollama is unreachable."""
    run_id = await _create_run_in_db(async_session)
    token = _register_and_login(test_client)

    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(
        side_effect=httpx.ConnectError("Connection refused")
    )
    mock_llm.warm_up = AsyncMock(return_value=None)

    with patch("app.api.routes.ai.get_llm_client", return_value=mock_llm):
        resp = test_client.post(
            "/api/v1/ai/advisor/config",
            json={"run_id": run_id},
            headers=_auth(token),
        )

    assert resp.status_code == 503, resp.text
    assert "unavailable" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_advisor_config_run_not_found_returns_404(test_client: TestClient, async_session):
    """POST /ai/advisor/config with non-existent run_id returns 404."""
    token = _register_and_login(test_client)
    non_existent = str(uuid.uuid4())

    resp = test_client.post(
        "/api/v1/ai/advisor/config",
        json={"run_id": non_existent},
        headers=_auth(token),
    )

    assert resp.status_code == 404, resp.text
