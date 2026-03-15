"""Submission endpoints.

Routes:
    POST   /assignments/{assignment_id}/submit            — submit a completed run for grading
    GET    /assignments/{assignment_id}/submissions/mine  — list current user's submissions
    GET    /assignments/{assignment_id}/preview-score     — preview checkpoint score (no submission)
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.assignment import Assignment
from app.models.enrollment import CourseEnrollment
from app.models.project import Project
from app.models.run import Run
from app.models.submission import Submission
from app.models.user import User
from app.schemas.submissions import PreviewScoreResponse, SubmissionResponse, SubmitRequest

router = APIRouter(tags=["submissions"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_assignment_or_404(assignment_id: uuid.UUID, db: AsyncSession) -> Assignment:
    """Fetch assignment by ID or raise 404."""
    assignment = await db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return assignment


async def _get_run_or_404(run_id: uuid.UUID, db: AsyncSession) -> Run:
    """Fetch run by ID or raise 404."""
    run = await db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


async def _verify_enrollment(
    course_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> None:
    """Raise 403 if user is not enrolled in the course."""
    result = await db.execute(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not enrolled in this course",
        )


async def _validate_locked_params(run: Run, assignment: Assignment) -> list[str]:
    """Return a list of error strings for locked param mismatches.

    locked_params values are stored as strings (coerced by schema validator).
    Compare against run.config dict by converting both sides to str.
    """
    errors: list[str] = []
    for param, required_value in (assignment.locked_params or {}).items():
        actual = (run.config or {}).get(param)
        if str(actual) != str(required_value):
            errors.append(
                f"{param} must be {required_value} — your run used {actual}"
            )
    return errors


# ---------------------------------------------------------------------------
# POST /assignments/{assignment_id}/submit
# ---------------------------------------------------------------------------

@router.post(
    "/assignments/{assignment_id}/submit",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_run(
    assignment_id: uuid.UUID,
    body: SubmitRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubmissionResponse:
    """Submit a completed run for grading.

    Validates:
    - Assignment exists and is open
    - User is enrolled in the course
    - Run belongs to the user and is in 'complete' status
    - Locked params in run.config match assignment.locked_params

    If validation passes, creates a Submission and dispatches evaluate_submission Celery task.
    Multiple submissions are allowed — highest score is retained by the frontend.
    """
    assignment = await _get_assignment_or_404(assignment_id, db)

    if not assignment.is_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignment is not open for submissions",
        )

    # Verify user enrollment
    await _verify_enrollment(assignment.course_id, user.id, db)

    # Fetch run and verify ownership + completion
    run = await _get_run_or_404(body.run_id, db)

    # Verify the run belongs to this user (via project.user_id)
    project = await db.get(Project, run.project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this run",
        )

    if run.status != "complete":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run must be in 'complete' status to submit (current: {run.status})",
        )

    # Validate locked params
    errors = await _validate_locked_params(run, assignment)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="; ".join(errors),
        )

    # Create submission
    submission = Submission(
        assignment_id=assignment_id,
        user_id=user.id,
        run_id=body.run_id,
        grading_status="pending",
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    # Dispatch evaluate_submission Celery task (import inside handler body to avoid circular imports)
    from worker.tasks.checkpoint_eval import evaluate_submission
    evaluate_submission.delay(str(submission.id))

    return SubmissionResponse.model_validate(submission)


# ---------------------------------------------------------------------------
# GET /assignments/{assignment_id}/submissions/mine
# ---------------------------------------------------------------------------

@router.get(
    "/assignments/{assignment_id}/submissions/mine",
    response_model=list[SubmissionResponse],
)
async def list_my_submissions(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SubmissionResponse]:
    """List all of the current user's submissions for this assignment.

    Returns submissions ordered by submitted_at descending (most recent first).
    Frontend displays the best score.
    """
    await _get_assignment_or_404(assignment_id, db)

    result = await db.execute(
        select(Submission)
        .where(
            Submission.assignment_id == assignment_id,
            Submission.user_id == user.id,
        )
        .order_by(Submission.submitted_at.desc())
    )
    submissions = result.scalars().all()
    return [SubmissionResponse.model_validate(s) for s in submissions]


# ---------------------------------------------------------------------------
# GET /assignments/{assignment_id}/preview-score
# ---------------------------------------------------------------------------

@router.get(
    "/assignments/{assignment_id}/preview-score",
    response_model=PreviewScoreResponse,
)
async def preview_score(
    assignment_id: uuid.UUID,
    run_id: uuid.UUID = Query(..., description="Run ID to preview score for"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PreviewScoreResponse:
    """Preview checkpoint score for a run without creating a submission.

    Computes the same evaluation that evaluate_submission would perform,
    but does not persist anything. Used by the frontend for live preview.
    """
    assignment = await _get_assignment_or_404(assignment_id, db)

    run = await _get_run_or_404(run_id, db)

    # Verify run ownership
    project = await db.get(Project, run.project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this run",
        )

    # Check locked params to determine eligibility
    errors = await _validate_locked_params(run, assignment)
    is_eligible = len(errors) == 0

    # Import evaluation function to compute preview
    from worker.tasks.checkpoint_eval import evaluate_checkpoint_rules
    ppa = run.ppa or {}
    checkpoint_rules = assignment.checkpoint_rules or {}
    checkpoint_results, score = evaluate_checkpoint_rules(ppa, checkpoint_rules)

    return PreviewScoreResponse(
        checkpoint_results=checkpoint_results,
        score=score,
        is_eligible=is_eligible,
    )
