"""Docker SDK wrapper for ORFS container lifecycle management.

Security constraints enforced on every container:
  - network_mode="none"     : No network access (CRITICAL — containers run untrusted code)
  - cap_drop=["ALL"]        : Drop all Linux capabilities
  - security_opt=["no-new-privileges"] : Prevent privilege escalation
  - mem_limit / memswap_limit : Hard RAM cap, no swap
  - cpu_period / cpu_quota  : CPU bandwidth limit via CFS scheduler

Note: read_only is NOT set on the container root. CLAUDE.md mandates this because
OpenROAD may write temp files outside WORK_HOME (e.g. /root). Security is provided
by --network none + cgroup limits + cap_drop instead.

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
        target: str,
        locked_args: list[str],
        settings: dict[str, Any],
    ) -> Any:
        """Spawn an isolated ORFS container and return the container object.

        Args:
            run_id: Unique run identifier used for container naming.
            image: ORFS Docker image (e.g. openroad/orfs:latest).
            workspace_path: Host path to the student workspace directory.
                            Mounted read-write at /workspace inside container.
            target: Make target to run (e.g. "synth", "route", "finish").
                    Maps from target_stage DB field via STAGE_TO_TARGET in orfs_job.py.
            locked_args: List of "KEY=VALUE" strings for instructor-locked params
                         (e.g. ["CLOCK_PERIOD=10", "PLATFORM=sky130hd"]).
                         Appended after target in the Make command — highest priority.
            settings: Dict with JOB_CPU_CORES, JOB_RAM_GB, JOB_DISK_GB keys.

        Note on PDK: ORFS bundles all platform files (sky130hd, gf180, asap7)
        inside the image at /OpenROAD-flow-scripts/flow/platforms/. No external
        PDK volume mount is needed or correct. PDK_ROOT is an OpenLane variable
        and is NOT used by ORFS.

        The caller MUST call stop_and_remove() in a finally block.
        """
        cpu_cores = settings["JOB_CPU_CORES"]
        ram_gb = settings["JOB_RAM_GB"]

        # ORFS Make invocation:
        #   --file  : explicit Makefile path (not -C which changes directory)
        #   DESIGN_CONFIG : absolute path to student's config.mk inside container
        #   WORK_HOME : CRITICAL — redirects ALL output (results/logs/reports/objects)
        #               to /workspace. Without this, output goes relative to the Make
        #               working directory (inside the read-only ORFS install tree).
        #   target  : the Make target stage (synth/floorplan/place/cts/route/finish)
        #   locked_args : instructor-locked parameters override config.mk
        command = [
            "make",
            "--file=/OpenROAD-flow-scripts/flow/Makefile",
            "DESIGN_CONFIG=/workspace/config.mk",
            "WORK_HOME=/workspace",
            target,
            *locked_args,
        ]

        return self._client.containers.run(
            image=image,
            command=command,
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
            # DO NOT set read_only=True — OpenROAD may write temp files outside WORK_HOME.
            # Security is enforced via network_mode=none + cap_drop + cgroup limits.
            # tmpfs /tmp: 2g required — Yosys uses /tmp heavily during synthesis.
            tmpfs={"/tmp": "size=2g"},
            # Security hardening
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            # Volume mounts — workspace only. NO PDK mount: ORFS bundles all PDKs
            # inside the image at /OpenROAD-flow-scripts/flow/platforms/.
            volumes={
                workspace_path: {"bind": "/workspace", "mode": "rw"},
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
