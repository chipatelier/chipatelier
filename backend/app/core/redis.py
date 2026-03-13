"""Redis async connection pool."""
from redis.asyncio import ConnectionPool, Redis

from app.core.config import get_settings

_pool: ConnectionPool | None = None


def _get_pool() -> ConnectionPool:
    """Lazily create and return the connection pool."""
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = ConnectionPool.from_url(settings.REDIS_URL, decode_responses=False)
    return _pool


async def get_redis() -> Redis:
    """Return a Redis client backed by the shared connection pool."""
    return Redis(connection_pool=_get_pool())


async def close_redis() -> None:
    """Close the connection pool (call on app shutdown)."""
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
