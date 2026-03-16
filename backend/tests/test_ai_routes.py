"""Tests for AI endpoint auth and chat stub.

NOTE: The 501 tests for explain/advisor endpoints were moved to
  tests/ai/test_explain_routes.py and tests/ai/test_advisor_routes.py
  in Plan 03-02, when those endpoints were wired to Ollama.

Remaining tests here:
  - test_ai_endpoints_require_auth  — all AI routes return 401 without token
  - test_chat_returns_501           — chat is still stubbed (Plan 03)
  - test_ollama_client_is_instantiable — OllamaClient constructor smoke test
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
# Auth gate tests (all endpoints return 401 without token)
# ---------------------------------------------------------------------------

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
# Chat stub test (chat still returns 501 — Plan 03 wires it)
# ---------------------------------------------------------------------------

def test_chat_returns_501(test_client):
    """POST /api/v1/ai/chat returns 501."""
    token = _register_and_login(test_client)
    resp = test_client.post(
        "/api/v1/ai/chat",
        json={"run_id": str(uuid.uuid4()), "message": "hello", "history": []},
        headers=auth_headers(token),
    )
    assert resp.status_code == 501, resp.text


# ---------------------------------------------------------------------------
# LLM client smoke test
# ---------------------------------------------------------------------------

def test_ollama_client_is_instantiable():
    """OllamaClient can be instantiated with a base_url (Phase 3 — fully implemented)."""
    client = OllamaClient(base_url="http://localhost:11434")
    assert client._model == "deepseek-r1:7b"
    assert client._client is not None
