"""Container lifecycle tests — plan 01-03.

Covers JOB-02: ORFS container security constraints and cleanup.
"""
import uuid
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_container_spawned_with_correct_limits(mock_docker):
    """ORFS container is spawned with CPU, RAM cgroup limits and network isolation."""
    from worker.container.manager import ContainerManager

    manager = ContainerManager()
    settings = {
        "JOB_CPU_CORES": 6,
        "JOB_RAM_GB": 8,
        "JOB_DISK_GB": 5,
    }
    run_id = str(uuid.uuid4())
    manager.run_container(
        run_id=run_id,
        image="openroad/orfs:latest",
        workspace_path="/tmp/ws",
        target="finish",
        locked_args=[],
        settings=settings,
    )

    call_kwargs = mock_docker.return_value.containers.run.call_args
    assert call_kwargs is not None
    kwargs = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]

    assert kwargs["mem_limit"] == "8g"
    assert kwargs["memswap_limit"] == "8g"
    assert kwargs["cpu_quota"] == 600000  # 6 * 100000
    assert kwargs["cpu_period"] == 100000


def test_container_has_no_network(mock_docker):
    """ORFS container runs with network_mode='none' for security isolation."""
    from worker.container.manager import ContainerManager

    manager = ContainerManager()
    run_id = str(uuid.uuid4())
    manager.run_container(
        run_id=run_id,
        image="openroad/orfs:latest",
        workspace_path="/tmp/ws",
        target="finish",
        locked_args=[],
        settings={"JOB_CPU_CORES": 4, "JOB_RAM_GB": 4, "JOB_DISK_GB": 5},
    )

    call_kwargs = mock_docker.return_value.containers.run.call_args
    kwargs = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]

    assert kwargs["network_mode"] == "none"


def test_container_security_options(mock_docker):
    """ORFS container has cap_drop=ALL, no-new-privileges, tmpfs=2g (no read_only per CLAUDE.md)."""
    from worker.container.manager import ContainerManager

    manager = ContainerManager()
    run_id = str(uuid.uuid4())
    manager.run_container(
        run_id=run_id,
        image="openroad/orfs:latest",
        workspace_path="/tmp/ws",
        target="finish",
        locked_args=[],
        settings={"JOB_CPU_CORES": 4, "JOB_RAM_GB": 4, "JOB_DISK_GB": 5},
    )

    call_kwargs = mock_docker.return_value.containers.run.call_args
    kwargs = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]

    # read_only is NOT set — CLAUDE.md: OpenROAD writes temp files outside WORK_HOME;
    # security provided by network_mode=none + cap_drop + cgroup limits instead.
    assert kwargs.get("read_only") is not True
    assert kwargs["cap_drop"] == ["ALL"]
    assert "no-new-privileges" in kwargs["security_opt"]
    # tmpfs 2g — Yosys uses /tmp heavily during synthesis (CLAUDE.md)
    assert "/tmp" in kwargs["tmpfs"]
    assert "2g" in kwargs["tmpfs"]["/tmp"]


def test_container_name_includes_run_id(mock_docker):
    """Container is named orfs_job_{run_id} for orphan detection."""
    from worker.container.manager import ContainerManager

    manager = ContainerManager()
    run_id = "abc123"
    manager.run_container(
        run_id=run_id,
        image="openroad/orfs:latest",
        workspace_path="/tmp/ws",
        target="finish",
        locked_args=[],
        settings={"JOB_CPU_CORES": 4, "JOB_RAM_GB": 4, "JOB_DISK_GB": 5},
    )

    call_kwargs = mock_docker.return_value.containers.run.call_args
    kwargs = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]

    assert kwargs["name"] == "orfs_job_abc123"


def test_container_volumes(mock_docker):
    """Container mounts workspace rw — no PDK volume (ORFS bundles PDKs internally)."""
    from worker.container.manager import ContainerManager

    manager = ContainerManager()
    run_id = str(uuid.uuid4())
    manager.run_container(
        run_id=run_id,
        image="openroad/orfs:latest",
        workspace_path="/tmp/my_workspace",
        target="finish",
        locked_args=[],
        settings={"JOB_CPU_CORES": 4, "JOB_RAM_GB": 4, "JOB_DISK_GB": 5},
    )

    call_kwargs = mock_docker.return_value.containers.run.call_args
    kwargs = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]

    volumes = kwargs["volumes"]
    assert "/tmp/my_workspace" in volumes
    assert volumes["/tmp/my_workspace"]["mode"] == "rw"
    # PDK_ROOT is an OpenLane variable — NOT used by ORFS. ORFS bundles all platform
    # files (sky130hd, gf180, asap7) inside the image at /OpenROAD-flow-scripts/flow/platforms/.
    assert "/data/pdks" not in volumes


def test_container_cleaned_up_on_completion(mock_docker):
    """stop_and_remove is called after successful container execution."""
    from worker.container.manager import ContainerManager

    manager = ContainerManager()
    run_id = str(uuid.uuid4())
    container = manager.run_container(
        run_id=run_id,
        image="openroad/orfs:latest",
        workspace_path="/tmp/ws",
        target="finish",
        locked_args=[],
        settings={"JOB_CPU_CORES": 4, "JOB_RAM_GB": 4, "JOB_DISK_GB": 5},
    )

    manager.stop_and_remove(container)

    container.stop.assert_called_once()
    container.remove.assert_called_once()


def test_container_cleaned_up_on_failure(mock_docker):
    """stop_and_remove is safe to call even when container is already gone."""
    from worker.container.manager import ContainerManager
    from docker.errors import NotFound

    manager = ContainerManager()
    container_name = "orfs_job_gone"

    # Simulate container already removed
    mock_docker.return_value.containers.get.side_effect = NotFound("not found")

    # Should not raise
    manager.stop_and_remove(container_name)


def test_stop_and_remove_not_found_is_silent(mock_docker):
    """stop_and_remove silently handles NotFound — container already removed."""
    from worker.container.manager import ContainerManager
    from docker.errors import NotFound

    manager = ContainerManager()
    mock_docker.return_value.containers.get.side_effect = NotFound("gone")
    # Must not raise
    manager.stop_and_remove("orfs_job_missing")


def test_list_orfs_containers(mock_docker):
    """list_orfs_containers returns structured info from docker container list."""
    from worker.container.manager import ContainerManager

    mock_container = MagicMock()
    mock_container.name = "orfs_job_abc123"
    mock_container.status = "running"
    mock_container.id = "containerid"
    mock_docker.return_value.containers.list.return_value = [mock_container]

    manager = ContainerManager()
    result = manager.list_orfs_containers()

    assert len(result) == 1
    assert result[0]["run_id"] == "abc123"
    assert result[0]["status"] == "running"
