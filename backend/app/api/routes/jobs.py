"""Job lifecycle endpoints.

Routes:
    POST   /jobs/submit    — submit an ORFS flow job
    GET    /jobs/{id}      — get job status
    DELETE /jobs/{id}      — cancel a job
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
from app.schemas.jobs import RunStatusResponse, SubmitRequest, SubmitResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

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

@router.post("/submit", response_model=SubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_job(
    body: SubmitRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubmitResponse:
    """Submit an ORFS flow job.

    Validates project ownership, enforces single-active-run constraint,
    creates a Run record, and dispatches the Celery orfs_job task.
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

    # Create Run record
    run = Run(
        project_id=body.project_id,
        status="queued",
        target_stage=body.target_stage,
        config=body.config_overrides if body.config_overrides else None,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Dispatch Celery task — import here to avoid circular imports at module load time
    from worker.tasks.orfs_job import run_orfs_job

    result = run_orfs_job.delay(str(run.id))

    # Store Celery task ID for cancel
    run.celery_task_id = result.id
    await db.commit()

    return SubmitResponse(run_id=run.id, status="queued")


# ---------------------------------------------------------------------------
# GET /jobs/{id} — Get job status
# ---------------------------------------------------------------------------

@router.get("/{run_id}", response_model=RunStatusResponse)
async def get_job_status(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RunStatusResponse:
    """Return current status and metrics for a run."""
    run = await _get_run_or_404(run_id, db)

    # Verify ownership via project
    project = await db.get(Project, run.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return RunStatusResponse.model_validate(run)


# ---------------------------------------------------------------------------
# DELETE /jobs/{id} — Cancel a job
# ---------------------------------------------------------------------------

@router.delete("/{run_id}", status_code=status.HTTP_200_OK)
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
        from worker.celery_app import app as celery_app  # noqa: F401 used in tests as mock target
        celery_app.control.revoke(
            run.celery_task_id,
            terminate=True,
            signal="SIGTERM",
        )

    return {"status": "cancelled", "run_id": str(run_id)}
