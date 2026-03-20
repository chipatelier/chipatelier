"""Tests for DELETE/PATCH/GET-source/GET-config project endpoints."""
import uuid
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_user_and_project(test_client):
    """Register user, login, create project. Returns (token, project_id)."""
    email = f"user-{uuid.uuid4().hex[:8]}@ex.com"
    test_client.post("/api/v1/auth/register", json={"email": email, "password": "pass1234"})
    token = test_client.post("/api/v1/auth/login", json={"email": email, "password": "pass1234"}).json()["access_token"]
    proj = test_client.post("/api/v1/projects", json={"name": "myproj"}, headers=_auth_header(token)).json()
    return token, proj["id"]


def test_delete_project_success(test_client):
    token, pid = _make_user_and_project(test_client)
    with patch("app.tasks.storage_cleanup.purge_project_artifacts") as mock_purge:
        mock_purge.delay = MagicMock()
        resp = test_client.delete(f"/api/v1/projects/{pid}", headers=_auth_header(token))
    assert resp.status_code == 204
    # Project no longer accessible
    assert test_client.get(f"/api/v1/projects/{pid}", headers=_auth_header(token)).status_code == 404


def test_delete_project_forbidden(test_client):
    _, pid = _make_user_and_project(test_client)
    test_client.post("/api/v1/auth/register", json={"email": "other@ex.com", "password": "pass1234"})
    other_token = test_client.post("/api/v1/auth/login", json={"email": "other@ex.com", "password": "pass1234"}).json()["access_token"]
    resp = test_client.delete(f"/api/v1/projects/{pid}", headers=_auth_header(other_token))
    assert resp.status_code == 403


def test_patch_project_rename(test_client):
    token, pid = _make_user_and_project(test_client)
    resp = test_client.patch(f"/api/v1/projects/{pid}", json={"name": "renamed"}, headers=_auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["name"] == "renamed"


def test_patch_project_rename_duplicate_409(test_client):
    test_client.post("/api/v1/auth/register", json={"email": "dup@ex.com", "password": "pass1234"})
    token = test_client.post("/api/v1/auth/login", json={"email": "dup@ex.com", "password": "pass1234"}).json()["access_token"]
    test_client.post("/api/v1/projects", json={"name": "proj_a"}, headers=_auth_header(token))
    proj_b = test_client.post("/api/v1/projects", json={"name": "proj_b"}, headers=_auth_header(token)).json()
    resp = test_client.patch(f"/api/v1/projects/{proj_b['id']}", json={"name": "proj_a"}, headers=_auth_header(token))
    assert resp.status_code == 409


def test_get_source_404_when_no_upload(test_client):
    token, pid = _make_user_and_project(test_client)
    resp = test_client.get(f"/api/v1/projects/{pid}/source", headers=_auth_header(token))
    assert resp.status_code == 404


def test_get_config_returns_empty_when_no_save(test_client):
    token, pid = _make_user_and_project(test_client)
    resp = test_client.get(f"/api/v1/projects/{pid}/config", headers=_auth_header(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == ""
    assert data["version"] == 0


def test_patch_config_increments_version(test_client):
    token, pid = _make_user_and_project(test_client)

    # Override the storage dependency to use a mock
    from app.main import app
    from app.services.storage_service import get_storage_service

    mock_storage = MagicMock()
    mock_storage.upload_file = MagicMock(return_value="some-key")
    app.dependency_overrides[get_storage_service] = lambda: mock_storage

    try:
        resp = test_client.patch(
            f"/api/v1/projects/{pid}",
            json={"config_mk": "CLOCK_PERIOD = 10\n"},
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.json()["config_version"] == 1
    finally:
        # Don't clear all overrides — test_client fixture manages get_db override
        app.dependency_overrides.pop(get_storage_service, None)
