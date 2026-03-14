"""Job lifecycle endpoints.

Routes:
    POST   /jobs/submit          — submit an ORFS flow job
    GET    /jobs/{id}            — get job status (includes notes for owner)
    DELETE /jobs/{id}            — cancel a job
    GET    /jobs/{id}/logs       — log history (REST fallback for completed runs)
    PATCH  /runs/{id}/notes      — update private run notes (owner only)
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.project import Project
from app.models.run import Run
from app.models.user import User
from app.schemas.jobs import RunNotesUpdate, RunStatusResponse, SubmitRequest, SubmitResponse

router = APIRouter(tags=["jobs"])

# Active run statuses — used to enforce single-active-run constraint
_ACTIVE_STATUSES = {"queued", "starting", "running"}


def _check_project_ownership(project: Project, user: User) -> None:
    if project.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


async def _get_project_or_404(project_id: uuid.UUID, db: AsyncSession) -> Project:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


async def _get_run_or_404(run_id: uuid.UUID, db: AsyncSession) -> Run:
    run = await db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


# ---------------------------------------------------------------------------
# POST /jobs/submit — Submit a job
# ---------------------------------------------------------------------------

@router.post("/jobs/submit", response_model=SubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_job(
    body: SubmitRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubmitResponse:
    """Submit an ORFS flow job.

    Instructor/admin runs go directly to the high_priority Celery queue.
    Student runs enter the Redis fair-queue sorted set; the drain_queue beat task
    dispatches them to orfs_jobs when capacity is available.
    """
    # Validate project ownership
    project = await _get_project_or_404(body.project_id, db)
    _check_project_ownership(project, user)

    # Enforce single-active-run: at most one active run per project
    active_result = await db.execute(
        select(Run).where(
            Run.project_id == body.project_id,
            Run.status.in_(_ACTIVE_STATUSES),
        )
    )
    if active_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A run is already active for this project. Cancel it before submitting a new one.",
        )

    # Determine queue priority based on role
    is_privileged = user.role in ("instructor", "admin")
    queue_priority = "high_priority" if is_privileged else "normal"

    # Create Run record
    run = Run(
        project_id=body.project_id,
        status="queued",
        target_stage=body.target_stage,
        config=body.config_overrides if body.config_overrides else None,
        artifact_path=body.source_path,  # Set artifact_path to source location
        queue_priority=queue_priority,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    if is_privileged:
        # Instructor/admin: bypass fair queue — dispatch directly to high_priority Celery queue
        from app.core.celery_client import celery_app as _celery
        result = _celery.send_task(
            "tasks.orfs_job.run_orfs_job_high",
            args=[str(run.id)],
            queue="high_priority",
        )
        run.celery_task_id = result.id
        await db.commit()
    else:
        # Student: add to Redis fair queue sorted set
        # drain_queue beat task (every 5s) dispatches when capacity is available
        try:
            import redis as redis_lib
            from app.core.config import get_settings
            settings = get_settings()
            r = redis_lib.Redis.from_url(settings.REDIS_URL)
            from worker.tasks.fair_queue import enqueue_student_job
            enqueue_student_job(str(user.id), str(run.id), r)
        except Exception:
            # If Redis is unavailable (e.g., test environment), fall back to direct Celery dispatch
            from app.core.celery_client import celery_app as _celery
            result = _celery.send_task(
                "tasks.orfs_job.run_orfs_job",
                args=[str(run.id)],
                queue="orfs_jobs",
            )
            run.celery_task_id = result.id
            await db.commit()
        # celery_task_id will be set by drain_queue when the job is dispatched (production path)

    return SubmitResponse(run_id=run.id, status="queued", queue_priority=queue_priority)


# ---------------------------------------------------------------------------
# GET /jobs/{id} — Get job status (includes notes for owner)
# ---------------------------------------------------------------------------

@router.get("/jobs/{run_id}", response_model=RunStatusResponse)
async def get_job_status(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RunStatusResponse:
    """Return current status, metrics, and notes for a run (owner only)."""
    run = await _get_run_or_404(run_id, db)

    # Verify ownership via project
    project = await db.get(Project, run.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return RunStatusResponse.model_validate(run)


# ---------------------------------------------------------------------------
# DELETE /jobs/{id} — Cancel a job
# ---------------------------------------------------------------------------

@router.delete("/jobs/{run_id}", status_code=status.HTTP_200_OK)
async def cancel_job(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Cancel a queued or running job.

    Updates status to cancelled and revokes the Celery task.
    Container cleanup is handled by the finally block in run_orfs_job.
    """
    run = await _get_run_or_404(run_id, db)

    # Verify ownership via project
    project = await db.get(Project, run.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if run.status not in _ACTIVE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel run with status '{run.status}'. Only active runs can be cancelled.",
        )

    # Update status first
    run.status = "cancelled"
    await db.commit()

    # Revoke the Celery task — sends SIGTERM to the worker
    if run.celery_task_id:
        from app.core.celery_client import celery_app as _celery
        _celery.control.revoke(
            run.celery_task_id,
            terminate=True,
            signal="SIGTERM",
        )

    return {"status": "cancelled", "run_id": str(run_id)}


# ---------------------------------------------------------------------------
# GET /jobs/{id}/logs — Log history (REST fallback for completed runs)
# ---------------------------------------------------------------------------

@router.get("/jobs/{run_id}/logs")
async def get_log_history(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Return full log history for a run from Redis logbuf.

    Used by the frontend when navigating to a completed run (no live WS needed).
    Falls back gracefully if logbuf has expired (24hr TTL).

    Returns:
        {"lines": [...], "total": N}
    """
    run = await _get_run_or_404(run_id, db)

    # Verify ownership via project
    project = await db.get(Project, run.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    from app.core.redis import get_redis
    r = await get_redis()
    raw_lines: list[bytes] = await r.lrange(f"logbuf:{run_id}", 0, -1)
    lines = [
        raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
        for raw in raw_lines
    ]
    return {"lines": lines, "total": len(lines)}


# ---------------------------------------------------------------------------
# PATCH /runs/{id}/notes — Update private run notes (owner only)
# ---------------------------------------------------------------------------

@router.patch("/runs/{run_id}/notes", response_model=RunStatusResponse)
async def update_run_notes(
    run_id: uuid.UUID,
    body: RunNotesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RunStatusResponse:
    """Update the private notes on a run.

    Notes are only visible to the run owner — they are excluded from list endpoints
    and from other users' views. Passing notes=null clears the existing notes.
    """
    run = await db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    # Verify ownership via project
    project = await db.get(Project, run.project_id)
    if project is None or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this run",
        )

    run.notes = body.notes
    await db.commit()
    await db.refresh(run)
    return RunStatusResponse.model_validate(run)
