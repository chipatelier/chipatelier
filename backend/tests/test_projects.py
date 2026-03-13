"""Project API tests — plan 01-03.

Covers JOB-01: project CRUD and multi-file upload to MinIO.
"""
import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from app.models.project import Project
from app.models.run import Run
from app.models.user import User
from app.core.security import hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(client):
    """Register a test user and return the access token."""
    email = f"proj_{uuid.uuid4().hex[:8]}@test.com"
    r = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Test1234!",
        "display_name": "Test User",
    })
    assert r.status_code == 201
    r2 = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Test1234!",
    })
    assert r2.status_code == 200
    return r2.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_project(test_client):
    """POST /api/v1/projects creates a new project, returns 201 with id/name/pdk."""
    token = _register_and_login(test_client)

    resp = test_client.post(
        "/api/v1/projects",
        json={"name": "my_gcd_design", "pdk": "sky130hd"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "id" in data
    assert data["name"] == "my_gcd_design"
    assert data["pdk"] == "sky130hd"
    assert "created_at" in data


def test_create_project_unauthenticated(test_client):
    """POST /api/v1/projects returns 401 without a token."""
    resp = test_client.post("/api/v1/projects", json={"name": "x"})
    assert resp.status_code == 401


def test_create_project_default_pdk(test_client):
    """POST /api/v1/projects without pdk field defaults to sky130hd."""
    token = _register_and_login(test_client)
    resp = test_client.post(
        "/api/v1/projects",
        json={"name": "no_pdk_specified"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["pdk"] == "sky130hd"


def test_list_projects(test_client):
    """GET /api/v1/projects returns only the current user's projects."""
    token = _register_and_login(test_client)
    # Create two projects
    test_client.post("/api/v1/projects", json={"name": "proj_a"}, headers=auth_headers(token))
    test_client.post("/api/v1/projects", json={"name": "proj_b"}, headers=auth_headers(token))

    resp = test_client.get("/api/v1/projects", headers=auth_headers(token))
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "proj_a" in names
    assert "proj_b" in names


def test_get_project(test_client):
    """GET /api/v1/projects/{id} returns project details."""
    token = _register_and_login(test_client)
    create_resp = test_client.post(
        "/api/v1/projects", json={"name": "proj_get"}, headers=auth_headers(token)
    )
    proj_id = create_resp.json()["id"]

    resp = test_client.get(f"/api/v1/projects/{proj_id}", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["id"] == proj_id


def test_get_project_not_found(test_client):
    """GET /api/v1/projects/{nonexistent-id} returns 404."""
    token = _register_and_login(test_client)
    fake_id = str(uuid.uuid4())
    resp = test_client.get(f"/api/v1/projects/{fake_id}", headers=auth_headers(token))
    assert resp.status_code == 404


def test_get_project_ownership(test_client):
    """GET /api/v1/projects/{id} returns 403 when accessed by another user."""
    token_owner = _register_and_login(test_client)
    token_other = _register_and_login(test_client)

    create_resp = test_client.post(
        "/api/v1/projects", json={"name": "private_proj"}, headers=auth_headers(token_owner)
    )
    proj_id = create_resp.json()["id"]

    resp = test_client.get(f"/api/v1/projects/{proj_id}", headers=auth_headers(token_other))
    assert resp.status_code == 403


def test_upload_files_to_project(test_client, mock_s3):
    """POST /api/v1/projects/{id}/upload accepts multipart Verilog files.

    Uses a dependency override so uploads use a mock StorageService.
    """
    from app.main import app
    from app.services.storage_service import get_storage_service

    token = _register_and_login(test_client)
    create_resp = test_client.post(
        "/api/v1/projects", json={"name": "upload_test"}, headers=auth_headers(token)
    )
    proj_id = create_resp.json()["id"]

    verilog_content = b"module top(); endmodule"
    config_content = b"PLATFORM = sky130hd\nCLOCK_PERIOD = 10"

    mock_svc = MagicMock()
    mock_svc.upload_file.return_value = "projects/{}/v1/top.v".format(proj_id)
    app.dependency_overrides[get_storage_service] = lambda: mock_svc

    try:
        resp = test_client.post(
            f"/api/v1/projects/{proj_id}/upload",
            files=[
                ("files", ("top.v", io.BytesIO(verilog_content), "text/plain")),
                ("files", ("config.mk", io.BytesIO(config_content), "text/plain")),
            ],
            headers=auth_headers(token),
        )
    finally:
        app.dependency_overrides.pop(get_storage_service, None)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "source_path" in data


def test_upload_invalid_extension(test_client):
    """POST /api/v1/projects/{id}/upload rejects non-Verilog files."""
    from app.main import app
    from app.services.storage_service import get_storage_service

    token = _register_and_login(test_client)
    create_resp = test_client.post(
        "/api/v1/projects", json={"name": "bad_upload"}, headers=auth_headers(token)
    )
    proj_id = create_resp.json()["id"]

    mock_svc = MagicMock()
    app.dependency_overrides[get_storage_service] = lambda: mock_svc

    try:
        resp = test_client.post(
            f"/api/v1/projects/{proj_id}/upload",
            files=[("files", ("exploit.exe", io.BytesIO(b"bad"), "application/octet-stream"))],
            headers=auth_headers(token),
        )
    finally:
        app.dependency_overrides.pop(get_storage_service, None)

    assert resp.status_code == 422


def test_list_runs_for_project(test_client, async_session):
    """GET /api/v1/projects/{id}/runs returns list of RunSummary ordered newest first."""
    token = _register_and_login(test_client)
    create_resp = test_client.post(
        "/api/v1/projects", json={"name": "runs_proj"}, headers=auth_headers(token)
    )
    proj_id = create_resp.json()["id"]

    # No runs yet
    resp = test_client.get(f"/api/v1/projects/{proj_id}/runs", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json() == []
