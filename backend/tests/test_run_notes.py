"""Tests for run notes privacy and PATCH /runs/{id}/notes endpoint.

Notes are private: only visible to run owner via RunStatusResponse.
Notes excluded from RunSummary (list endpoint).
Other users get 403 when trying to PATCH notes they don't own.
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models.project import Project
from app.models.run import Run
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(client):
    email = f"notes_{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Test1234!",
        "display_name": "Notes User",
    })
    r2 = client.post("/api/v1/auth/login", json={"email": email, "password": "Test1234!"})
    return r2.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _create_project(client, token, name="notes_proj"):
    r = client.post(
        "/api/v1/projects",
        json={"name": name, "pdk": "sky130hd"},
        headers=auth_headers(token),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _create_run(async_session, proj_id):
    """Create a run directly in the test DB."""
    import asyncio

    async def _create():
        run = Run(
            project_id=uuid.UUID(proj_id),
            status="queued",
            target_stage="finish",
            queue_priority="normal",
        )
        async_session.add(run)
        await async_session.commit()
        await async_session.refresh(run)
        return str(run.id)

    return asyncio.get_event_loop().run_until_complete(_create())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_patch_notes_owner(test_client, async_session):
    """PATCH /api/v1/runs/{id}/notes returns 200 with updated notes for owner."""
    token = _register_and_login(test_client)
    proj_id = _create_project(test_client, token, "notes_owner_proj")

    # Create a run directly in the DB
    import asyncio
    async def _create():
        run = Run(
            project_id=uuid.UUID(proj_id),
            status="queued",
            target_stage="finish",
            queue_priority="normal",
        )
        async_session.add(run)
        await async_session.commit()
        await async_session.refresh(run)
        return str(run.id)
    run_id = asyncio.get_event_loop().run_until_complete(_create())

    resp = test_client.patch(
        f"/api/v1/runs/{run_id}/notes",
        json={"notes": "tried lower utilization"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["notes"] == "tried lower utilization"


def test_patch_notes_wrong_user_returns_403(test_client, async_session):
    """PATCH /api/v1/runs/{id}/notes by a different user returns 403."""
    token_owner = _register_and_login(test_client)
    token_other = _register_and_login(test_client)
    proj_id = _create_project(test_client, token_owner, "notes_owner_proj2")

    import asyncio
    async def _create():
        run = Run(
            project_id=uuid.UUID(proj_id),
            status="queued",
            target_stage="finish",
            queue_priority="normal",
        )
        async_session.add(run)
        await async_session.commit()
        await async_session.refresh(run)
        return str(run.id)
    run_id = asyncio.get_event_loop().run_until_complete(_create())

    # Other user tries to patch notes — should get 403
    resp = test_client.patch(
        f"/api/v1/runs/{run_id}/notes",
        json={"notes": "hacked notes"},
        headers=auth_headers(token_other),
    )
    assert resp.status_code == 403, resp.text


def test_run_list_excludes_notes(test_client, async_session):
    """GET /api/v1/projects/{id}/runs does NOT include 'notes' in response items."""
    token = _register_and_login(test_client)
    proj_id = _create_project(test_client, token, "notes_list_proj")

    import asyncio
    async def _create():
        run = Run(
            project_id=uuid.UUID(proj_id),
            status="queued",
            target_stage="finish",
            queue_priority="normal",
            notes="secret note",
        )
        async_session.add(run)
        await async_session.commit()
    asyncio.get_event_loop().run_until_complete(_create())

    resp = test_client.get(
        f"/api/v1/projects/{proj_id}/runs",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    runs = resp.json()
    assert len(runs) >= 1
    # notes must NOT be in the run summary items
    for run in runs:
        assert "notes" not in run, f"notes field should not appear in list response, got: {run}"


def test_patch_notes_nonexistent_run_returns_404(test_client):
    """PATCH /api/v1/runs/{id}/notes returns 404 for nonexistent run ID."""
    token = _register_and_login(test_client)
    fake_run_id = str(uuid.uuid4())
    resp = test_client.patch(
        f"/api/v1/runs/{fake_run_id}/notes",
        json={"notes": "ghost note"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 404, resp.text


def test_patch_notes_clears_with_null(test_client, async_session):
    """PATCH /api/v1/runs/{id}/notes with null clears the notes field."""
    token = _register_and_login(test_client)
    proj_id = _create_project(test_client, token, "notes_clear_proj")

    import asyncio
    async def _create():
        run = Run(
            project_id=uuid.UUID(proj_id),
            status="queued",
            target_stage="finish",
            queue_priority="normal",
            notes="initial note",
        )
        async_session.add(run)
        await async_session.commit()
        await async_session.refresh(run)
        return str(run.id)
    run_id = asyncio.get_event_loop().run_until_complete(_create())

    resp = test_client.patch(
        f"/api/v1/runs/{run_id}/notes",
        json={"notes": None},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["notes"] is None
