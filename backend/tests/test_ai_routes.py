"""Tests for AI endpoint stubs.

All AI routes return 501 Not Implemented in Phase 1.
Phase 3 wires Ollama to these endpoints without changing the interface.
"""
import uuid

import pytest

from app.ai.llm_client import OllamaClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(client):
    email = f"ai_{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Test1234!",
        "display_name": "AI Test User",
    })
    r2 = client.post("/api/v1/auth/login", json={"email": email, "password": "Test1234!"})
    return r2.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# AI endpoint stub tests (all return 501)
# ---------------------------------------------------------------------------

def test_explain_log_returns_501(test_client):
    """POST /api/v1/ai/explain/log returns 501 with appropriate message."""
    token = _register_and_login(test_client)
    resp = test_client.post(
        "/api/v1/ai/explain/log",
        json={"run_id": str(uuid.uuid4()), "log_lines": 100},
        headers=auth_headers(token),
    )
    assert resp.status_code == 501, resp.text
    assert "Phase 3" in resp.json()["detail"] or "not configured" in resp.json()["detail"]


def test_explain_timing_returns_501(test_client):
    """POST /api/v1/ai/explain/timing returns 501."""
    token = _register_and_login(test_client)
    resp = test_client.post(
        "/api/v1/ai/explain/timing",
        json={"run_id": str(uuid.uuid4()), "log_lines": 100},
        headers=auth_headers(token),
    )
    assert resp.status_code == 501, resp.text


def test_explain_drc_returns_501(test_client):
    """POST /api/v1/ai/explain/drc returns 501."""
    token = _register_and_login(test_client)
    resp = test_client.post(
        "/api/v1/ai/explain/drc",
        json={"run_id": str(uuid.uuid4()), "log_lines": 100},
        headers=auth_headers(token),
    )
    assert resp.status_code == 501, resp.text


def test_advisor_config_returns_501(test_client):
    """POST /api/v1/ai/advisor/config returns 501."""
    token = _register_and_login(test_client)
    resp = test_client.post(
        "/api/v1/ai/advisor/config",
        json={"run_id": str(uuid.uuid4())},
        headers=auth_headers(token),
    )
    assert resp.status_code == 501, resp.text


def test_chat_returns_501(test_client):
    """POST /api/v1/ai/chat returns 501."""
    token = _register_and_login(test_client)
    resp = test_client.post(
        "/api/v1/ai/chat",
        json={"run_id": str(uuid.uuid4()), "message": "hello", "history": []},
        headers=auth_headers(token),
    )
    assert resp.status_code == 501, resp.text


def test_ai_endpoints_require_auth(test_client):
    """All AI endpoints return 401 without authentication."""
    for url, body in [
        ("/api/v1/ai/explain/log", {"run_id": str(uuid.uuid4()), "log_lines": 100}),
        ("/api/v1/ai/explain/timing", {"run_id": str(uuid.uuid4()), "log_lines": 100}),
        ("/api/v1/ai/advisor/config", {"run_id": str(uuid.uuid4())}),
        ("/api/v1/ai/chat", {"run_id": str(uuid.uuid4()), "message": "hi", "history": []}),
    ]:
        resp = test_client.post(url, json=body)
        assert resp.status_code == 401, f"Expected 401 for {url}, got {resp.status_code}"


# ---------------------------------------------------------------------------
# LLM client stub test
# ---------------------------------------------------------------------------

def test_ollama_client_generate_raises_not_implemented():
    """OllamaClient.generate() raises NotImplementedError (Phase 3 stub)."""
    import asyncio
    client = OllamaClient(base_url="http://localhost:11434")
    with pytest.raises(NotImplementedError):
        asyncio.run(client.generate("test prompt"))
