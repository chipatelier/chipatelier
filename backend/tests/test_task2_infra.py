"""
Task 2 TDD tests: Alembic migrations, Celery config, Wave 0 pytest infrastructure.
RED phase - defines expected behavior before implementation.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestConftestFixtures:
    """conftest.py fixtures resolve without ImportError."""

    def test_async_session_fixture_resolves(self, async_session):
        """async_session fixture yields an AsyncSession."""
        from sqlalchemy.ext.asyncio import AsyncSession
        assert isinstance(async_session, AsyncSession)

    def test_test_client_fixture_resolves(self, test_client):
        """test_client fixture yields a TestClient."""
        from starlette.testclient import TestClient
        assert isinstance(test_client, TestClient)

    def test_mock_docker_fixture_resolves(self, mock_docker):
        """mock_docker fixture resolves without error."""
        assert mock_docker is not None

    def test_mock_s3_fixture_resolves(self, mock_s3):
        """mock_s3 fixture resolves without error."""
        assert mock_s3 is not None

    def test_mock_redis_fixture_resolves(self, mock_redis):
        """mock_redis fixture resolves without error."""
        assert mock_redis is not None


class TestMockDocker:
    """mock_docker.containers.run returns mock container with correct interface."""

    def test_mock_docker_containers_run_returns_container(self, mock_docker):
        """mock_docker.containers.run() returns a container mock."""
        client = mock_docker.return_value
        container = client.containers.run("test-image")
        assert container is not None

    def test_mock_container_has_logs(self, mock_docker):
        """Mock container has .logs() method returning iterable."""
        client = mock_docker.return_value
        container = client.containers.run("test-image")
        logs = list(container.logs())
        assert len(logs) > 0

    def test_mock_container_has_wait(self, mock_docker):
        """Mock container has .wait() method returning status dict."""
        client = mock_docker.return_value
        container = client.containers.run("test-image")
        result = container.wait()
        assert "StatusCode" in result
        assert result["StatusCode"] == 0

    def test_mock_container_has_attrs(self, mock_docker):
        """Mock container has .attrs with State.ExitCode."""
        client = mock_docker.return_value
        container = client.containers.run("test-image")
        assert "State" in container.attrs
        assert "ExitCode" in container.attrs["State"]


class TestMockS3:
    """mock_s3 (moto) has bucket 'chipatelier-artifacts' queryable via boto3."""

    def test_mock_s3_bucket_exists(self, mock_s3):
        """The chipatelier-artifacts bucket is pre-created in mock S3."""
        import boto3
        from moto import mock_aws
        # The fixture should have created the bucket; just verify it's accessible
        # mock_s3 is the boto3 client created inside moto context
        buckets = mock_s3.list_buckets()
        bucket_names = [b["Name"] for b in buckets.get("Buckets", [])]
        assert "chipatelier-artifacts" in bucket_names

    def test_mock_s3_can_put_object(self, mock_s3):
        """Objects can be stored in the mock S3 bucket."""
        mock_s3.put_object(
            Bucket="chipatelier-artifacts",
            Key="test/artifact.txt",
            Body=b"test content",
        )
        resp = mock_s3.get_object(Bucket="chipatelier-artifacts", Key="test/artifact.txt")
        assert resp["Body"].read() == b"test content"


class TestCeleryConfig:
    """Celery task_routes maps orfs_job.* to orfs_jobs queue."""

    def test_orfs_job_route(self):
        """orfs_job tasks are routed to orfs_jobs queue."""
        sys.path.insert(0, "/opt/developments/chipatelier")
        from worker.celeryconfig import task_routes
        assert "worker.tasks.orfs_job.*" in task_routes
        assert task_routes["worker.tasks.orfs_job.*"]["queue"] == "orfs_jobs"

    def test_tile_generator_route(self):
        """tile_generator tasks are routed to background queue."""
        from worker.celeryconfig import task_routes
        assert "worker.tasks.tile_generator.*" in task_routes
        assert task_routes["worker.tasks.tile_generator.*"]["queue"] == "background"

    def test_vnc_session_route(self):
        """vnc_session tasks are routed to background queue."""
        from worker.celeryconfig import task_routes
        assert "worker.tasks.vnc_session.*" in task_routes
        assert task_routes["worker.tasks.vnc_session.*"]["queue"] == "background"


class TestAlembicMigration:
    """Alembic revision file contains all required CREATE TABLE statements."""

    def test_migration_file_exists(self):
        """0001_initial_schema.py migration file exists."""
        import pathlib
        migration_file = pathlib.Path(
            "/opt/developments/chipatelier/backend/alembic/versions/0001_initial_schema.py"
        )
        assert migration_file.exists(), "Migration file not found"

    def test_migration_creates_users_table(self):
        """Migration creates users table."""
        with open("/opt/developments/chipatelier/backend/alembic/versions/0001_initial_schema.py") as f:
            content = f.read()
        assert "users" in content.lower()

    def test_migration_creates_projects_table(self):
        """Migration creates projects table."""
        with open("/opt/developments/chipatelier/backend/alembic/versions/0001_initial_schema.py") as f:
            content = f.read()
        assert "projects" in content.lower()

    def test_migration_creates_runs_table(self):
        """Migration creates runs table."""
        with open("/opt/developments/chipatelier/backend/alembic/versions/0001_initial_schema.py") as f:
            content = f.read()
        assert "runs" in content.lower()

    def test_migration_creates_vnc_sessions_table(self):
        """Migration creates vnc_sessions table."""
        with open("/opt/developments/chipatelier/backend/alembic/versions/0001_initial_schema.py") as f:
            content = f.read()
        assert "vnc_sessions" in content.lower()

    def test_migration_has_gin_indexes(self):
        """Migration creates GIN indexes for JSONB columns."""
        with open("/opt/developments/chipatelier/backend/alembic/versions/0001_initial_schema.py") as f:
            content = f.read()
        assert "GIN" in content or "gin" in content.lower()
