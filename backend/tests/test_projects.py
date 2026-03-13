"""Wave 0 stub: project API tests — implemented in plan 01-02."""
import pytest


async def test_create_project(test_client, async_session):
    """POST /api/v1/projects creates a new project."""
    pass


async def test_list_projects(test_client, async_session):
    """GET /api/v1/projects returns user's projects."""
    pass


async def test_list_runs_for_project(test_client, async_session):
    """GET /api/v1/projects/{id}/runs returns runs for a project."""
    pass
