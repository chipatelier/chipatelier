"""ORFS job execution Celery task.

Runs a full RTL-to-GDS ORFS flow in an isolated Docker container.
Streams log lines to Redis pubsub and a Redis list buffer for later replay.
Updates run status in PostgreSQL synchronously (SQLAlchemy sync engine).

Stage transition detection inserts separator lines into the log stream at each
ORFS flow stage boundary, using the reliable pattern from flow.sh:
  "Running <script>.tcl, stage <stage_id>"
This is more reliable than content-based patterns because flow.sh always prints
this line exactly once before each stage, regardless of stage content.

Container lifecycle:
  - Warm pool container claimed if available; cold start otherwise
  - Container is ALWAYS stopped and removed in the finally block
  - Workspace directory is ALWAYS removed in the finally block
  - These invariants hold even if the task is revoked via Celery control.revoke()

Auto-retry policy:
  - Retries ONCE after 30s on transient Docker API errors (DockerException on start)
  - Does NOT retry on non-zero exit code (design error — user must fix Verilog/SDC)
  - Does NOT retry on timeout (JOB_TIMEOUT_SECONDS exceeded)
"""
import glob as glob_mod
import os
import re
import shutil
from datetime import datetime, timezone

import redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from celery_app import app
from container.manager import ContainerManager

# ---------------------------------------------------------------------------
# Stage → Make target mapping
# ---------------------------------------------------------------------------

STAGE_TO_TARGET: dict[str, str] = {
    "synth": "synth",
    "floorplan": "floorplan",
    "place": "place",
    "cts": "cts",
    "route": "route",
    "finish": "finish",
}

# ---------------------------------------------------------------------------
# Stage transition detection — reliable pattern from flow.sh
# ---------------------------------------------------------------------------

# flow.sh prints this before every stage:
#   "Running floorplan.tcl, stage 2_1_floorplan"
#   "Running cts.tcl, stage 4_1_cts"
#   "Running global_route.tcl, stage 5_1_grt"
# The stage_id (group 2) maps directly to the JSON metrics filename.
STAGE_LINE_PATTERN = re.compile(r"Running (\S+\.tcl), stage (\S+)")

# Map stage_id prefix to friendly name for UI display
STAGE_ID_TO_NAME: dict[str, str] = {
    "1_": "SYNTHESIS",
    "2_": "FLOORPLAN",
    "3_": "PLACEMENT",
    "4_": "CTS",
    "5_1_grt": "GLOBAL ROUTE",
    "5_2": "DETAIL ROUTE",
    "6_": "FINISH",
}

# Visual separator injected into log stream at each stage transition
SEPARATOR_FMT = "═══ {stage} ══════════════════════════════════"

# Maximum log lines to keep in Redis buffer (LRU-trimmed)
LOG_BUFFER_MAX = 5000

# Redis key TTL for log buffer: 24 hours
LOG_BUFFER_TTL = 86400


# ---------------------------------------------------------------------------
# GRT failure detection
# ---------------------------------------------------------------------------

def _check_grt_failure(workspace: str) -> bool:
    """Return True if GRT congestion failure ODB exists in the workspace.

    ORFS global route can fail with congestion but exit 0. It writes
    5_1_grt-failed.odb instead of 5_1_grt.odb in this case.
    Use glob to find it without needing PLATFORM/DESIGN_NAME.
    """
    pattern = os.path.join(workspace, "results", "*", "*", "base", "5_1_grt-failed.odb")
    return bool(glob_mod.glob(pattern))


# ---------------------------------------------------------------------------
# Main ORFS job task (student queue / normal priority)
# ---------------------------------------------------------------------------

@app.task(
    name="tasks.orfs_job.run_orfs_job",
    queue="orfs_jobs",
    bind=True,
    acks_late=True,
    max_retries=1,
    default_retry_delay=30,
)
def run_orfs_job(self, run_id: str) -> None:
    """Execute an ORFS flow job in an isolated Docker container.

    Status transitions:
        queued → starting → running → complete | failed | timeout | cancelled

    Guarantees:
        - Container is always removed in finally block
        - Workspace directory is always cleaned up in finally block
        - Log lines published to Redis logs:{run_id} pubsub channel
        - Last 5000 log lines kept in Redis list logbuf:{run_id}

    Retry policy:
        - Retries once after 30s on DockerException (transient tool crash / OOM)
        - Does NOT retry on non-zero exit code (design error — user must fix code)
        - Does NOT retry on timeout
    """
    import docker.errors as docker_errors
    from app.core.config import get_settings

    settings = get_settings()

    # Use synchronous SQLAlchemy engine — Celery tasks are synchronous
    sync_db_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://", "postgresql://"
    ).replace("sqlite+aiosqlite://", "sqlite://")
    engine = create_engine(sync_db_url)

    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)
    manager = ContainerManager()
    container = None
    workspace = f"/tmp/workspace_{run_id}"

    def publish_line(line: str) -> None:
        """Publish a log line to Redis pubsub and append to the replay buffer."""
        channel = f"logs:{run_id}"
        list_key = f"logbuf:{run_id}"
        encoded = line.encode("utf-8")
        redis_client.publish(channel, encoded)
        redis_client.rpush(list_key, encoded)
        redis_client.ltrim(list_key, -LOG_BUFFER_MAX, -1)
        redis_client.expire(list_key, LOG_BUFFER_TTL)

    def update_status(status: str, stage: str | None = None) -> None:
        """Update run status and optionally stage_completed in PostgreSQL."""
        with Session(engine) as db:
            db.execute(
                text(
                    "UPDATE runs "
                    "SET status = :s, "
                    "    stage_completed = COALESCE(:st, stage_completed), "
                    "    completed_at = CASE "
                    "        WHEN :s IN ('complete', 'failed', 'cancelled', 'timeout') "
                    "        THEN :now "
                    "        ELSE completed_at "
                    "    END "
                    "WHERE id = :id"
                ),
                {
                    "s": status,
                    "st": stage,
                    "id": run_id,
                    "now": datetime.now(timezone.utc),
                },
            )
            db.commit()

    # Attempt to claim a pre-started container from the warm pool
    try:
        from container.warm_pool import get_warm_pool
        pool = get_warm_pool()
        warm_container_id = pool.claim() if pool else None
    except Exception:
        pool = None
        warm_container_id = None

    try:
        os.makedirs(workspace, exist_ok=True)
        update_status("starting")
        publish_line(f"[chipatelier] Starting ORFS job {run_id}")

        # Fetch artifact_path, target_stage, and config snapshot from DB
        with Session(engine) as db:
            row = db.execute(
                text("SELECT artifact_path, target_stage, config FROM runs WHERE id = :id"),
                {"id": run_id},
            ).first()
            artifact_path = row.artifact_path if row else None
            target_stage = (row.target_stage if row else None) or "finish"
            config_snapshot = (row.config if row else None) or {}

        # Map target_stage DB field to ORFS Make target
        make_target = STAGE_TO_TARGET.get(target_stage, "finish")

        # Extract instructor-locked params from config snapshot (stored by submission endpoint)
        # e.g. {"CLOCK_PERIOD": "10", "PLATFORM": "sky130hd"} → ["CLOCK_PERIOD=10", "PLATFORM=sky130hd"]
        locked_params = config_snapshot.get("locked_params", {})
        locked_args = [f"{k}={v}" for k, v in locked_params.items()]

        # Download source files from MinIO into workspace
        if artifact_path:
            _download_workspace(settings, artifact_path, workspace)

        if warm_container_id:
            # Warm container available: use it instead of cold-starting
            try:
                container = manager._client.containers.get(warm_container_id)
                publish_line(f"[chipatelier] Using warm container {warm_container_id[:12]}")
            except docker_errors.NotFound:
                # Stale warm container — fall through to cold start
                warm_container_id = None
                container = None

        if container is None:
            # Cold start path (warm pool miss, stale container, or pool empty)
            try:
                container = manager.run_container(
                    run_id=run_id,
                    image=settings.ORFS_IMAGE,
                    workspace_path=workspace,
                    target=make_target,
                    locked_args=locked_args,
                    settings={
                        "JOB_CPU_CORES": settings.JOB_CPU_CORES,
                        "JOB_RAM_GB": settings.JOB_RAM_GB,
                        "JOB_DISK_GB": settings.JOB_DISK_GB,
                    },
                )
            except docker_errors.DockerException as exc:
                # Transient Docker API error — retry once after 30s
                # Design errors (bad Verilog) do NOT trigger this: container runs then exits non-zero
                update_status("queued")  # back to queued for retry
                publish_line(f"[chipatelier] Docker error on start — retrying in 30s: {exc}")
                raise self.retry(exc=exc, countdown=30)

        update_status("running")

        # Stream stdout/stderr line by line
        # Stage transitions detected via flow.sh reliable pattern:
        #   "Running <script>.tcl, stage <stage_id>"
        for raw_line in container.logs(stream=True, follow=True):
            line = raw_line.decode("utf-8", errors="replace").rstrip()

            # Check for stage transition marker from flow.sh
            m = STAGE_LINE_PATTERN.search(line)
            if m:
                stage_id = m.group(2)  # e.g. "2_1_floorplan"
                # Determine friendly name from prefix match
                stage_name = next(
                    (name for prefix, name in STAGE_ID_TO_NAME.items() if stage_id.startswith(prefix)),
                    stage_id.upper()
                )
                separator = SEPARATOR_FMT.format(stage=stage_name)
                publish_line(separator)
                update_status("running", stage_id)

            publish_line(line)

        # Wait for container to exit and capture exit code
        result = container.wait(timeout=settings.JOB_TIMEOUT_SECONDS)
        exit_code = result.get("StatusCode", 1)

        # GRT congestion failure: exit code may be 0 but 5_1_grt-failed.odb is written
        # instead of 5_1_grt.odb. Must check for this file explicitly.
        grt_failed = _check_grt_failure(workspace)
        if grt_failed:
            final_status = "failed"
            publish_line("[chipatelier] GRT congestion failure detected (5_1_grt-failed.odb found) — marking failed")
        else:
            final_status = "complete" if exit_code == 0 else "failed"

        update_status(final_status)
        publish_line(f"[chipatelier] Job {run_id} finished with status: {final_status}")

        # Do NOT retry design errors — user must fix their Verilog/SDC
        if final_status == "complete":
            try:
                from tasks.tile_generator import generate_png
                generate_png.delay(run_id, workspace)
            except Exception:
                pass  # tile generation is a background enhancement, not critical

    except self.MaxRetriesExceededError:
        update_status("failed")
        publish_line(f"[chipatelier] Job {run_id} failed after retry — marking failed")

    except Exception as exc:
        update_status("failed")
        publish_line(f"[chipatelier] Job {run_id} failed with exception: {exc!r}")
        raise

    finally:
        # INVARIANT: container and workspace are ALWAYS cleaned up
        if container is not None:
            manager.stop_and_remove(container)
        # Replenish warm pool slot consumed by this job
        if pool is not None:
            try:
                pool.replenish()
            except Exception:
                pass
        shutil.rmtree(workspace, ignore_errors=True)


# ---------------------------------------------------------------------------
# High-priority variant (instructor/admin jobs)
# ---------------------------------------------------------------------------

@app.task(
    name="tasks.orfs_job.run_orfs_job_high",
    queue="high_priority",
    bind=True,
    acks_late=True,
    max_retries=1,
    default_retry_delay=30,
)
def run_orfs_job_high(self, run_id: str) -> None:
    """High-priority variant for instructor/admin jobs.

    Identical logic to run_orfs_job; routed to high_priority queue so it
    bypasses the student fair queue and is processed before student jobs.
    """
    # Delegate to the main task implementation (same logic, different queue binding)
    return run_orfs_job(self, run_id)


# ---------------------------------------------------------------------------
# Helper: download project source files from MinIO into workspace
# ---------------------------------------------------------------------------

def _download_workspace(settings: object, artifact_path: str, workspace: str) -> None:
    """Download all files from MinIO artifact_path prefix into the workspace directory.

    Creates ORFS-compatible directory structure:
      /workspace/config.mk (config file)
      /workspace/src/design/*.v (Verilog files)

    If MinIO is unreachable (e.g., in test environments), this function
    silently skips the download — the workspace may be pre-populated.
    """
    try:
        import boto3
        from botocore.config import Config

        s3 = boto3.client(
            "s3",
            endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

        # Create ORFS directory structure
        src_dir = os.path.join(workspace, "src", "design")
        os.makedirs(src_dir, exist_ok=True)

        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=settings.S3_BUCKET_ARTIFACTS,
            Prefix=artifact_path,
        ):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                filename = key.split("/")[-1]

                # config.mk goes to workspace root, Verilog files go to src/design/
                if filename.endswith(".mk"):
                    dest = os.path.join(workspace, filename)
                else:
                    dest = os.path.join(src_dir, filename)

                s3.download_file(settings.S3_BUCKET_ARTIFACTS, key, dest)
    except Exception:
        # Don't fail the job if source download fails — let ORFS report the error
        pass
