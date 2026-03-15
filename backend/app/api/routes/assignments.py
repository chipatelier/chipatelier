"""Assignment endpoints.

Routes:
    POST   /courses/{course_id}/assignments        — create assignment (instructor-only)
    GET    /courses/{course_id}/assignments        — list assignments (enrolled/instructor)
    PATCH  /assignments/{assignment_id}/open       — toggle is_open (instructor-only)
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.routes.courses import _require_instructor
from app.core.database import get_db
from app.models.assignment import Assignment
from app.models.course import Course
from app.models.enrollment import CourseEnrollment
from app.models.user import User
from app.schemas.assignments import AssignmentCreate, AssignmentOpenToggle, AssignmentResponse

router = APIRouter(tags=["assignments"])


async def _get_course_or_404(course_id: uuid.UUID, db: AsyncSession) -> Course:
    """Fetch course by ID or raise 404."""
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


async def _get_assignment_or_404(assignment_id: uuid.UUID, db: AsyncSession) -> Assignment:
    """Fetch assignment by ID or raise 404."""
    assignment = await db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return assignment


def _require_course_instructor(course: Course, user: User) -> None:
    """Raise 403 if user is not the instructor who owns this course (or admin)."""
    if user.role == "admin":
        return
    if user.role != "instructor" or course.instructor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


# ---------------------------------------------------------------------------
# POST /courses/{course_id}/assignments — Create assignment
# ---------------------------------------------------------------------------

@router.post(
    "/courses/{course_id}/assignments",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assignment(
    course_id: uuid.UUID,
    body: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssignmentResponse:
    """Create an assignment under a course. Instructor role + course ownership required."""
    _require_instructor(user)
    course = await _get_course_or_404(course_id, db)
    _require_course_instructor(course, user)

    assignment = Assignment(
        course_id=course_id,
        title=body.title,
        description=body.description,
        pdk=body.pdk,
        target_stage=body.target_stage,
        locked_params=body.locked_params,
        editable_params=body.editable_params,
        checkpoint_rules=body.checkpoint_rules,
        due_at=body.due_at,
        orfs_version=body.orfs_version,
        is_open=False,  # always hidden on creation
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return AssignmentResponse.model_validate(assignment)


# ---------------------------------------------------------------------------
# GET /courses/{course_id}/assignments — List assignments
# ---------------------------------------------------------------------------

@router.get("/courses/{course_id}/assignments", response_model=list[AssignmentResponse])
async def list_assignments(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AssignmentResponse]:
    """List assignments for a course.

    - Instructors (course owner): see all assignments regardless of is_open
    - Students: must be enrolled; only see assignments where is_open=True
    - Admin: sees all assignments
    """
    course = await _get_course_or_404(course_id, db)

    if user.role == "admin" or (user.role == "instructor" and course.instructor_id == user.id):
        # Instructor or admin: show all assignments
        result = await db.execute(
            select(Assignment)
            .where(Assignment.course_id == course_id)
            .order_by(Assignment.created_at.asc())
        )
    else:
        # Student: verify enrollment, then show only open assignments
        enrollment = await db.execute(
            select(CourseEnrollment).where(
                CourseEnrollment.course_id == course_id,
                CourseEnrollment.user_id == user.id,
            )
        )
        if enrollment.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not enrolled in this course",
            )
        result = await db.execute(
            select(Assignment)
            .where(Assignment.course_id == course_id, Assignment.is_open == True)  # noqa: E712
            .order_by(Assignment.created_at.asc())
        )

    assignments = result.scalars().all()
    return [AssignmentResponse.model_validate(a) for a in assignments]


# ---------------------------------------------------------------------------
# PATCH /assignments/{assignment_id}/open — Toggle is_open
# ---------------------------------------------------------------------------

@router.patch("/assignments/{assignment_id}/open", response_model=AssignmentResponse)
async def toggle_assignment_open(
    assignment_id: uuid.UUID,
    body: AssignmentOpenToggle,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssignmentResponse:
    """Toggle is_open on an assignment. Course instructor role required."""
    _require_instructor(user)
    assignment = await _get_assignment_or_404(assignment_id, db)

    # Verify caller owns the course that contains this assignment
    course = await _get_course_or_404(assignment.course_id, db)
    _require_course_instructor(course, user)

    assignment.is_open = body.is_open
    await db.commit()
    await db.refresh(assignment)
    return AssignmentResponse.model_validate(assignment)
