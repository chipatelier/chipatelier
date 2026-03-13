"""Docker SDK wrapper for ORFS container lifecycle management.

Security constraints enforced on every container:
  - network_mode="none"     : No network access (CRITICAL — containers run untrusted code)
  - read_only=True          : Filesystem is read-only; writes only allowed in /tmp (tmpfs)
  - cap_drop=["ALL"]        : Drop all Linux capabilities
  - security_opt=["no-new-privileges"] : Prevent privilege escalation
  - user="orfs:orfs"        : Run as unprivileged user (not root)
  - mem_limit / memswap_limit : Hard RAM cap, no swap
  - cpu_period / cpu_quota  : CPU bandwidth limit via CFS scheduler

Note on storage-opt size=:
  storage-opt size={N}G requires the Docker daemon to use the overlay2 storage driver
  with the 'pquota' mount option on RHEL/Rocky 9. To enable:
    1. Edit /etc/docker/daemon.json: {"storage-driver": "overlay2"}
    2. Mount /var/lib/docker on a filesystem with pquota option in /etc/fstab
    3. Restart dockerd
  Until that is configured, disk quotas should be enforced at the OS level
  (filesystem quotas on the workspace directory).
"""
from typing import Any

import docker
from docker.errors import APIError, NotFound


class ContainerManager:
    """Manages ORFS Docker container lifecycle."""

    def __init__(self) -> None:
        self._client = docker.from_env()

    def run_container(
        self,
        run_id: str,
        image: str,
        workspace_path: str,
        pdk_root: str,
        settings: dict[str, Any],
    ) -> Any:
        """Spawn an isolated ORFS container and return the container object.

        The caller MUST call stop_and_remove() in a finally block.
        """
        cpu_cores = settings["JOB_CPU_CORES"]
        ram_gb = settings["JOB_RAM_GB"]

        return self._client.containers.run(
            image=image,
            command=["make", "DESIGN_CONFIG=/workspace/config.mk"],
            name=f"orfs_job_{run_id}",
            detach=True,
            # CRITICAL: no network access — containers run untrusted student code
            network_mode="none",
            # CPU limits via CFS bandwidth controller
            cpu_period=100000,
            cpu_quota=cpu_cores * 100000,
            # RAM limits — no swap (memswap == mem_limit)
            mem_limit=f"{ram_gb}g",
            memswap_limit=f"{ram_gb}g",
            # Read-only filesystem with tmpfs scratch space
            read_only=True,
            tmpfs={"/tmp": "size=512m"},
            # Security hardening
            user="orfs:orfs",
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            # Volume mounts
            volumes={
                workspace_path: {"bind": "/workspace", "mode": "rw"},
                pdk_root: {"bind": "/pdks", "mode": "ro"},
            },
            # Disk quota via storage-opt requires overlay2 + pquota mount on RHEL/Rocky 9.
            # See module docstring for enablement instructions.
            # Uncomment when overlay2 + pquota is confirmed available:
            # storage_opt={"size": f"{settings['JOB_DISK_GB']}G"},
        )

    def stop_and_remove(
        self,
        container_or_name: Any,
        timeout: int = 10,
    ) -> None:
        """Stop and remove a container by object or name.

        Silently handles NotFound — container may already be removed (expected
        during cancellation or watchdog cleanup races).
        """
        try:
            if isinstance(container_or_name, str):
                container = self._client.containers.get(container_or_name)
            else:
                container = container_or_name
            container.stop(timeout=timeout)
            container.remove(force=True)
        except NotFound:
            pass  # Already removed — this is fine

    def list_orfs_containers(self) -> list[dict[str, str]]:
        """Return all containers whose name starts with 'orfs_job_'.

        Used by the orphaned-container watchdog beat task.
        Returns list of dicts with keys: name, run_id, status, id.
        """
        containers = self._client.containers.list(filters={"name": "orfs_job_"})
        return [
            {
                "name": c.name,
                "run_id": c.name.replace("orfs_job_", "", 1),
                "status": c.status,
                "id": c.id,
            }
            for c in containers
        ]
