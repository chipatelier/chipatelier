"""Click-to-inspect query endpoint tests — plan 02-05.

Tests the GET /api/v1/query/{run_id} endpoint which runs OpenROAD as a subprocess
to perform spatial queries on ODB files.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.models.run import Run  # noqa: F401 — import to catch ImportError early
import json


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(client: TestClient, email: str, password: str = "securepass1") -> str:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": email.split("@")[0]},
    )
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


async def _create_user_with_completed_run(
    client: TestClient,
    async_session,
    email: str,
    artifact_path: str | None = "artifacts/test-run-path",
) -> tuple[str, str]:
    """Create a user + project + completed run. Returns (token, run_id)."""
    from app.models.project import Project
    from app.models.run import Run
    from app.models.user import User

    token = _register_and_login(client, email)
    me_resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    user_id = me_resp.json()["id"]

    project = Project(
        user_id=uuid.UUID(user_id),
        name="Test Project",
        pdk="sky130hd",
    )
    async_session.add(project)
    await async_session.flush()

    run = Run(
        project_id=project.id,
        status="complete",
        stage_completed="route",
        artifact_path=artifact_path,
        ppa={"drc_violations": 0, "worst_negative_slack": -0.05},
    )
    async_session.add(run)
    await async_session.commit()

    return token, str(run.id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_click_to_inspect_hit(test_client: TestClient, async_session):
    """LAYT-02: Click within a cell returns cell name, master, and net names."""
    token, run_id = await _create_user_with_completed_run(
        test_client, async_session, "query_hit@example.com"
    )

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = json.dumps([
        {"name": "u_reg0", "master": "sky130_fd_sc_hd__dfxtp_1", "nets": ["clk", "q", "d"]}
    ])

    with patch("app.api.routes.query.subprocess.run", return_value=mock_proc) as mock_run:
        with patch("app.api.routes.query.StorageService") as mock_storage_cls:
            mock_storage_inst = MagicMock()
            mock_storage_inst.download_file_to_path = MagicMock(return_value=None)
            mock_storage_cls.return_value = mock_storage_inst

            resp = test_client.get(
                f"/api/v1/query/{run_id}",
                params={"x_um": 100.5, "y_um": 200.3, "tolerance_um": 1.0},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "elements" in data
    assert len(data["elements"]) == 1
    elem = data["elements"][0]
    assert elem["name"] == "u_reg0"
    assert elem["master"] == "sky130_fd_sc_hd__dfxtp_1"
    assert "clk" in elem["nets"]
    assert data["run_id"] == run_id
    assert data["x_um"] == 100.5
    assert data["y_um"] == 200.3


@pytest.mark.asyncio
async def test_click_to_inspect_miss(test_client: TestClient, async_session):
    """LAYT-02: Click outside any cell returns empty list (not 404)."""
    token, run_id = await _create_user_with_completed_run(
        test_client, async_session, "query_miss@example.com"
    )

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = json.dumps([])

    with patch("app.api.routes.query.subprocess.run", return_value=mock_proc):
        with patch("app.api.routes.query.StorageService") as mock_storage_cls:
            mock_storage_inst = MagicMock()
            mock_storage_inst.download_file_to_path = MagicMock(return_value=None)
            mock_storage_cls.return_value = mock_storage_inst

            resp = test_client.get(
                f"/api/v1/query/{run_id}",
                params={"x_um": 999.0, "y_um": 999.0},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["elements"] == []


@pytest.mark.asyncio
async def test_query_non_owner_run_returns_403(test_client: TestClient, async_session):
    """Querying a run owned by another user returns 403."""
    _owner_token, run_id = await _create_user_with_completed_run(
        test_client, async_session, "owner_run@example.com"
    )
    other_token = _register_and_login(test_client, "other_user_query@example.com")

    with patch("app.api.routes.query.subprocess.run") as mock_run:
        with patch("app.api.routes.query.StorageService"):
            resp = test_client.get(
                f"/api/v1/query/{run_id}",
                params={"x_um": 100.0, "y_um": 200.0},
                headers={"Authorization": f"Bearer {other_token}"},
            )

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    # subprocess must NOT be called for unauthorized access
    mock_run.assert_not_called()


@pytest.mark.asyncio
async def test_query_run_without_artifacts_returns_400(test_client: TestClient, async_session):
    """Querying a run with no artifact_path returns 400."""
    token, run_id = await _create_user_with_completed_run(
        test_client, async_session, "no_artifacts_query@example.com",
        artifact_path=None,
    )

    with patch("app.api.routes.query.subprocess.run") as mock_run:
        with patch("app.api.routes.query.StorageService"):
            resp = test_client.get(
                f"/api/v1/query/{run_id}",
                params={"x_um": 100.0, "y_um": 200.0},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    mock_run.assert_not_called()
