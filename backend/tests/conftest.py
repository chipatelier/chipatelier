"""
Wave 0 pytest fixtures — used by all test plans in Phase 1.
Provides: async_session, test_client, mock_docker, mock_s3, mock_redis.
"""
import asyncio
import os
from collections.abc import AsyncGenerator
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

# Ensure test environment has minimal required env vars
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing")

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.models.base import Base
import app.models  # noqa: F401 — register all models


# ---------------------------------------------------------------------------
# Async engine (SQLite in-memory for speed; all schema created via metadata)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    """Session-scoped SQLite in-memory engine with schema."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Function-scoped session with rollback on teardown."""
    session_factory = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def test_client(async_session):
    """TestClient with get_db dependency overridden to use in-memory DB."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db

    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Mock Docker SDK
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def mock_docker():
    """Mock docker.from_env() with a realistic container mock."""
    with patch("docker.from_env") as mock:
        mock_container = MagicMock()
        mock_container.logs.return_value = iter([b"test log line\n"])
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.attrs = {"State": {"ExitCode": 0}}
        mock.return_value.containers.run.return_value = mock_container
        yield mock


# ---------------------------------------------------------------------------
# Mock S3 / MinIO via moto
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def mock_s3():
    """Moto-backed S3 mock with chipatelier-artifacts bucket pre-created."""
    try:
        import boto3
        from moto import mock_aws

        with mock_aws():
            client = boto3.client(
                "s3",
                region_name="us-east-1",
                aws_access_key_id="test",
                aws_secret_access_key="test",
            )
            client.create_bucket(Bucket="chipatelier-artifacts")
            yield client
    except ImportError:
        # moto not installed — yield a MagicMock
        yield MagicMock()


# ---------------------------------------------------------------------------
# Mock Redis (fakeredis)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def mock_redis():
    """Fakeredis async client for testing Redis-dependent code."""
    try:
        import fakeredis.aioredis as fakeredis_aioredis
        yield fakeredis_aioredis.FakeRedis()
    except (ImportError, AttributeError):
        try:
            import fakeredis
            yield fakeredis.FakeRedis()
        except ImportError:
            from unittest.mock import AsyncMock
            yield AsyncMock()
