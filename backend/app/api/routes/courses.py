"""Course and enrollment endpoints.

Routes:
    POST   /courses                             — create course (instructor-only)
    GET    /courses                             — list enrolled/taught courses
    POST   /courses/{course_id}/enroll         — student enrolls via code
    GET    /courses/{course_id}/dashboard      — per-student progress (instructor-only)
    GET    /courses/{course_id}/dashboard/export — CSV download (instructor-only)
"""
import csv
import io
import secrets
import string
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.course import Course
from app.models.enrollment import CourseEnrollment
from app.models.project import Project
from app.models.run import Run
from app.models.submission import Submission
from app.models.user import User
from app.schemas.courses import CourseCreate, CourseResponse, EnrollRequest, EnrollResponse

router = APIRouter(prefix="/courses", tags=["courses"])

# ---------------------------------------------------------------------------
# Enrollment code generation
# ---------------------------------------------------------------------------

# Safe alphabet: uppercase A-Z without O and I; digits 1-9 without 0
# Removes characters easily confused visually (O/0, I/1)
_SAFE_ALPHA = (
    string.ascii_uppercase.replace("O", "").replace("I", "")
)
_SAFE_DIGITS = string.digits.replace("0", "")
_SAFE_ALPHABET = _SAFE_ALPHA + _SAFE_DIGITS


def generate_enrollment_code() -> str:
    """Generate a collision-safe enrollment code in VLSI-YYYY-XXXX format.

    Uses secrets.choice for cryptographic randomness.
    Alphabet excludes O, I (alpha) and 0 (digit) to prevent visual confusion.
    """
    year = datetime.now(timezone.utc).year
    segment = "".join(secrets.choice(_SAFE_ALPHABET) for _ in range(4))
    return f"VLSI-{year}-{segment}"


async def _generate_unique_code(db: AsyncSession) -> str:
    """Generate a DB-unique enrollment code with up to 10 retry attempts.

    Raises HTTP 500 if all attempts fail (extremely unlikely — safe alphabet
    has 31 chars ^ 4 = ~923k combinations).
    """
    for _ in range(10):
        code = generate_enrollment_code()
        existing = await db.execute(
            select(Course).where(Course.enrollment_code == code)
        )
        if existing.scalar_one_or_none() is None:
            return code
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to generate a unique enrollment code — please retry",
    )


# ---------------------------------------------------------------------------
# Role guard helper
# ---------------------------------------------------------------------------

def _require_instructor(user: User) -> None:
    """Raise 403 if the current user is not an instructor or admin."""
    if user.role not in ("instructor", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


# ---------------------------------------------------------------------------
# POST /courses — Create course
# ---------------------------------------------------------------------------

@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    body: CourseCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CourseResponse:
    """Create a new course. Instructor role required."""
    _require_instructor(user)

    code = await _generate_unique_code(db)
    course = Course(
        instructor_id=user.id,
        name=body.name,
        term=body.term,
        enrollment_code=code,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return CourseResponse.model_validate(course)


# ---------------------------------------------------------------------------
# GET /courses — List courses for current user
# ---------------------------------------------------------------------------

@router.get("", response_model=list[CourseResponse])
async def list_courses(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CourseResponse]:
    """Return courses the user teaches (instructor) or is enrolled in (student)."""
    if user.role in ("instructor", "admin"):
        result = await db.execute(
            select(Course)
            .where(Course.instructor_id == user.id)
            .order_by(Course.created_at.desc())
        )
    else:
        # Join with enrollments to get student's courses
        result = await db.execute(
            select(Course)
            .join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
            .where(CourseEnrollment.user_id == user.id)
            .order_by(Course.created_at.desc())
        )
    courses = result.scalars().all()
    return [CourseResponse.model_validate(c) for c in courses]


# ---------------------------------------------------------------------------
# POST /courses/{course_id}/enroll — Student enrollment
# ---------------------------------------------------------------------------

@router.post("/{course_id}/enroll", response_model=EnrollResponse)
async def enroll_in_course(
    course_id: uuid.UUID,
    body: EnrollRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EnrollResponse:
    """Enroll in a course using an enrollment code.

    Returns 404 if the code is not found on this course.
    Returns 409 if the user is already enrolled.
    """
    # Verify course exists
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    # Verify enrollment code matches this specific course
    if course.enrollment_code != body.enrollment_code:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid enrollment code")

    # Check for duplicate enrollment
    existing = await db.execute(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already enrolled in this course")

    enrollment = CourseEnrollment(
        course_id=course_id,
        user_id=user.id,
    )
    db.add(enrollment)
    try:
        await db.commit()
        await db.refresh(enrollment)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already enrolled in this course")

    return EnrollResponse(
        course_id=course.id,
        course_name=course.name,
        enrolled_at=enrollment.enrolled_at,
    )


# ---------------------------------------------------------------------------
# GET /courses/{course_id}/dashboard — Instructor dashboard
# ---------------------------------------------------------------------------

@router.get("/{course_id}/dashboard")
async def get_course_dashboard(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Per-student progress dashboard for instructors.

    Returns students[] with display_name, run_count, last_run_status,
    submission_status, score — plus queue_info with queued/running counts.

    Instructor role required (403 for students).
    """
    _require_instructor(user)

    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    # Verify this instructor owns the course (or is admin)
    if course.instructor_id != user.id and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    # Fetch all enrolled students
    enrollments_result = await db.execute(
        select(CourseEnrollment, User)
        .join(User, User.id == CourseEnrollment.user_id)
        .where(CourseEnrollment.course_id == course_id)
        .order_by(User.display_name)
    )
    enrollments = enrollments_result.all()

    # Import Assignment model to get course assignment IDs (used to filter submissions)
    from app.models.assignment import Assignment as AssignmentModel

    course_assignment_ids_result = await db.execute(
        select(AssignmentModel.id).where(AssignmentModel.course_id == course_id)
    )
    course_assignment_ids = [row[0] for row in course_assignment_ids_result.all()]

    students = []
    for enrollment, student in enrollments:
        # Count runs for this student across all their projects
        run_count_result = await db.execute(
            select(func.count(Run.id))
            .join(Project, Run.project_id == Project.id)
            .where(Project.user_id == student.id)
        )
        run_count = run_count_result.scalar_one() or 0

        # Get last run status across all student projects
        last_run_result = await db.execute(
            select(Run)
            .join(Project, Run.project_id == Project.id)
            .where(Project.user_id == student.id)
            .order_by(Run.created_at.desc())
            .limit(1)
        )
        last_run = last_run_result.scalar_one_or_none()
        last_run_status = last_run.status if last_run else None

        # Get best submission score for this course's assignments
        if course_assignment_ids:
            best_sub_result = await db.execute(
                select(func.max(Submission.score))
                .where(
                    Submission.user_id == student.id,
                    Submission.assignment_id.in_(course_assignment_ids),
                )
            )
            best_score = best_sub_result.scalar_one_or_none()
            sub_exists_result = await db.execute(
                select(Submission)
                .where(
                    Submission.user_id == student.id,
                    Submission.assignment_id.in_(course_assignment_ids),
                )
                .limit(1)
            )
        else:
            best_score = None
            sub_exists_result = None

        has_submission = (
            sub_exists_result is not None
            and sub_exists_result.scalar_one_or_none() is not None
        )
        submission_status = "submitted" if has_submission else "not_submitted"

        students.append({
            "display_name": student.display_name or student.email,
            "user_id": str(student.id),
            "run_count": run_count,
            "last_run_status": last_run_status,
            "submission_status": submission_status,
            "score": float(best_score) if best_score is not None else None,
        })

    # Queue depth — attempt Redis, fall back to 0 on error
    queued = 0
    running = 0
    try:
        from app.core.redis import get_redis
        r = await get_redis()
        # fair_queue:normal is a sorted set (ZADD in jobs.py)
        queued = await r.zcard("fair_queue:normal") or 0
    except Exception:
        pass

    return {
        "students": students,
        "queue_info": {"queued": int(queued), "running": int(running)},
    }


# ---------------------------------------------------------------------------
# GET /courses/{course_id}/dashboard/export — CSV export
# ---------------------------------------------------------------------------

@router.get("/{course_id}/dashboard/export")
async def export_course_dashboard_csv(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Export per-student results as a CSV file download.

    Columns: student_display_name, submission_date, score.
    Instructor role required (403 for students).
    Content-Disposition: attachment header triggers browser download.
    """
    _require_instructor(user)

    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if course.instructor_id != user.id and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    # Fetch all submissions for this course's assignments with user info
    from app.models.assignment import Assignment as AssignmentModel
    course_assignment_ids_result = await db.execute(
        select(AssignmentModel.id).where(AssignmentModel.course_id == course_id)
    )
    course_assignment_ids = [row[0] for row in course_assignment_ids_result.all()]

    if not course_assignment_ids:
        # No assignments — return empty CSV
        result_rows: list = []
    else:
        result = await db.execute(
            select(Submission, User)
            .join(User, User.id == Submission.user_id)
            .where(Submission.assignment_id.in_(course_assignment_ids))
            .order_by(User.display_name, Submission.submitted_at.desc())
        )
        result_rows = result.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["student_display_name", "submission_date", "score"])
    for submission, student in result_rows:
        writer.writerow([
            student.display_name or student.email,
            submission.submitted_at.isoformat() if submission.submitted_at else "",
            submission.score if submission.score is not None else "",
        ])
    output.seek(0)

    return StreamingResponse(
        iter([output.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=grades-{course_id}.csv"},
    )
