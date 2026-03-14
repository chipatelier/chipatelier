"""
Warm pool of pre-started ORFS containers.

Why: ORFS container cold start takes 5-10s (image pull check + Docker overhead).
Pre-starting WARM_POOL_SIZE/2 containers reduces job start latency to <1s.

Pool state stored in Redis list key "warm_pool:available" (list of container IDs).
A Celery beat task (replenish_warm_pool) runs every 30s to maintain pool size.

Security: Warm containers run with the same resource constraints as job containers
EXCEPT they do not have --network none (they're not executing student code yet).
Network isolation is applied when the student workspace is mounted and ORFS starts.

On claim(): container ID is returned; caller renames/configures it for the job.
On claim() returning None: caller spawns a cold-start container (graceful degradation).
"""
import uuid
from typing import Optional

import docker
import redis as redis_lib
from docker.errors import APIError, NotFound

POOL_KEY = "warm_pool:available"


class WarmPool:
    """Pre-started ORFS container pool backed by a Redis list."""

    def __init__(self, settings):
        self._settings = settings
        self._docker = docker.from_env()
        self._redis = redis_lib.Redis.from_url(settings.REDIS_URL)
        # Target size: WARM_POOL_SIZE / 2 (configurable)
        self._target_size = max(1, settings.WARM_POOL_SIZE // 2)

    def claim(self) -> Optional[str]:
        """Pop a container ID from the warm pool.

        Returns container ID string, or None if pool is empty or container is stale.
        Caller must call replenish() after claiming to maintain pool size.
        """
        container_id = self._redis.lpop(POOL_KEY)
        if container_id is None:
            return None
        cid = container_id.decode() if isinstance(container_id, bytes) else container_id
        # Verify container is still running (may have crashed since it was added)
        try:
            c = self._docker.containers.get(cid)
            if c.status != "running":
                c.remove(force=True)
                return None  # pool slot was stale; caller falls back to cold start
            return cid
        except NotFound:
            return None  # container already gone

    def replenish(self) -> bool:
        """Start one new warm container and add it to the pool.

        Called after a claim() and on the beat schedule every 30s.
        Returns True if a container was started successfully.
        Returns False if pool is already at target size or start fails.
        """
        current_size = self._redis.llen(POOL_KEY)
        if current_size >= self._target_size:
            return False  # pool is full

        warm_id = str(uuid.uuid4())[:8]
        container_name = f"orfs_warm_{warm_id}"
        try:
            c = self._docker.containers.run(
                image=self._settings.ORFS_IMAGE,
                name=container_name,
                detach=True,
                command=["sleep", "infinity"],  # idle; workspace mounted at claim time
                # Same resource limits as job containers (except network isolation — not yet)
                cpu_period=100000,
                cpu_quota=self._settings.JOB_CPU_CORES * 100000,
                mem_limit=f"{self._settings.JOB_RAM_GB}g",
                memswap_limit=f"{self._settings.JOB_RAM_GB}g",
                cap_drop=["ALL"],
                security_opt=["no-new-privileges"],
                # No workspace volume yet — mounted when job is claimed
            )
            self._redis.rpush(POOL_KEY, c.id)
            self._redis.expire(POOL_KEY, 7200)  # 2hr TTL on pool list
            return True
        except (APIError, Exception):
            return False  # non-fatal: job falls back to cold start

    def drain(self) -> int:
        """Stop and remove all warm containers. Called on worker shutdown.

        Returns the number of containers successfully removed.
        """
        count = 0
        while True:
            cid = self._redis.lpop(POOL_KEY)
            if cid is None:
                break
            cid = cid.decode() if isinstance(cid, bytes) else cid
            try:
                self._docker.containers.get(cid).remove(force=True)
                count += 1
            except NotFound:
                pass  # already gone
        return count


# ---------------------------------------------------------------------------
# Module-level singleton — initialized by Celery worker startup signal
# ---------------------------------------------------------------------------

_pool: Optional[WarmPool] = None


def get_warm_pool() -> Optional[WarmPool]:
    """Return the current WarmPool singleton, or None if not initialized."""
    global _pool
    return _pool


def init_warm_pool(settings) -> WarmPool:
    """Initialize the WarmPool singleton. Called on worker_ready signal."""
    global _pool
    _pool = WarmPool(settings)
    return _pool
