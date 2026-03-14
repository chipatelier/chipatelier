"""Tests for the container warm pool.

Uses MagicMock for Docker SDK and fakeredis for Redis isolation.
"""
import pytest
from unittest.mock import MagicMock, patch
import fakeredis


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.ORFS_IMAGE = "openroad/orfs:latest"
    s.JOB_CPU_CORES = 4
    s.JOB_RAM_GB = 8
    s.WARM_POOL_SIZE = 4
    s.REDIS_URL = "redis://localhost:6379/0"
    return s


def _make_pool(mock_settings, mock_docker=None, fake_r=None):
    """Helper to construct a WarmPool with mocked docker and Redis."""
    if fake_r is None:
        fake_r = fakeredis.FakeRedis()
    if mock_docker is None:
        mock_docker = MagicMock()

    with patch("worker.container.warm_pool.docker.from_env", return_value=mock_docker), \
         patch("worker.container.warm_pool.redis_lib.Redis.from_url", return_value=fake_r):
        from worker.container.warm_pool import WarmPool
        pool = WarmPool(mock_settings)
    return pool, mock_docker, fake_r


def test_claim_returns_none_when_empty(mock_settings):
    """WarmPool.claim() returns None when the pool list is empty."""
    pool, _, _ = _make_pool(mock_settings)
    assert pool.claim() is None


def test_replenish_adds_container_to_pool(mock_settings):
    """WarmPool.replenish() starts a container and adds its ID to Redis."""
    mock_docker = MagicMock()
    mock_container = MagicMock()
    mock_container.id = "abc123"
    mock_docker.containers.run.return_value = mock_container
    fake_r = fakeredis.FakeRedis()

    pool, _, _ = _make_pool(mock_settings, mock_docker=mock_docker, fake_r=fake_r)
    result = pool.replenish()

    assert result is True
    assert fake_r.llen("warm_pool:available") == 1


def test_claim_after_replenish(mock_settings):
    """After replenish(), claim() returns the container ID and pool empties."""
    mock_docker = MagicMock()
    mock_container = MagicMock()
    mock_container.id = "abc123"
    mock_container.status = "running"
    mock_docker.containers.run.return_value = mock_container
    mock_docker.containers.get.return_value = mock_container
    fake_r = fakeredis.FakeRedis()

    pool, _, _ = _make_pool(mock_settings, mock_docker=mock_docker, fake_r=fake_r)
    pool.replenish()
    claimed = pool.claim()

    assert claimed == "abc123"
    # Pool is empty after claim
    assert pool.claim() is None


def test_claim_removes_stale_container(mock_settings):
    """claim() removes a crashed/stopped container from the pool and returns None."""
    from docker.errors import NotFound
    mock_docker = MagicMock()
    mock_docker.containers.get.side_effect = NotFound("gone")
    fake_r = fakeredis.FakeRedis()
    # Manually add a container ID to the pool
    fake_r.rpush("warm_pool:available", "dead-container-id")

    pool, _, _ = _make_pool(mock_settings, mock_docker=mock_docker, fake_r=fake_r)
    claimed = pool.claim()

    # Stale container ID removed; claim returns None (caller falls back to cold start)
    assert claimed is None


def test_replenish_does_not_exceed_target_size(mock_settings):
    """replenish() is a no-op when the pool is already at target size."""
    mock_docker = MagicMock()
    mock_container = MagicMock()
    mock_container.id = "abc123"
    mock_docker.containers.run.return_value = mock_container
    fake_r = fakeredis.FakeRedis()

    pool, _, _ = _make_pool(mock_settings, mock_docker=mock_docker, fake_r=fake_r)
    # Target size is WARM_POOL_SIZE // 2 = 2
    target = pool._target_size
    # Pre-fill pool to target size
    for i in range(target):
        fake_r.rpush("warm_pool:available", f"container-{i}")

    result = pool.replenish()
    assert result is False  # pool already full


def test_drain_removes_all_containers(mock_settings):
    """drain() stops and removes all containers and clears the pool."""
    mock_docker = MagicMock()
    mock_container = MagicMock()
    mock_docker.containers.get.return_value = mock_container
    fake_r = fakeredis.FakeRedis()
    fake_r.rpush("warm_pool:available", "c1", "c2", "c3")

    pool, _, _ = _make_pool(mock_settings, mock_docker=mock_docker, fake_r=fake_r)
    count = pool.drain()

    assert count == 3
    assert fake_r.llen("warm_pool:available") == 0
