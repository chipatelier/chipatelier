"""Course and enrollment endpoints.

Routes:
    POST   /courses                         — create course (instructor-only)
    GET    /courses                         — list enrolled/taught courses
    POST   /courses/{course_id}/enroll     — student enrolls via code
"""
import secrets
import string
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.course import Course
from app.models.enrollment import CourseEnrollment
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
    year = datetime.utcnow().year
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
