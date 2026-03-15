"""Wave 0 stubs for course and enrollment tests — Phase 2 plan 02-02 implements these."""
import pytest

from app.models.course import Course  # noqa: F401 — import to catch errors early
from app.models.enrollment import CourseEnrollment  # noqa: F401


@pytest.mark.skip(reason="Wave 0 stub — implement in plan 02-02")
def test_enrollment_code_format():
    """COUR-02: Enrollment code must match VLSI-YYYY-XXXX format."""
    ...


@pytest.mark.skip(reason="Wave 0 stub — implement in plan 02-02")
def test_create_course_instructor_only():
    """COUR-02: Only users with role=instructor can create a course."""
    ...


@pytest.mark.skip(reason="Wave 0 stub — implement in plan 02-02")
def test_enroll_success():
    """COUR-03: Student can enroll with a valid enrollment code."""
    ...


@pytest.mark.skip(reason="Wave 0 stub — implement in plan 02-02")
def test_enroll_invalid_code():
    """COUR-03: Enrollment with unknown code returns 404."""
    ...


@pytest.mark.skip(reason="Wave 0 stub — implement in plan 02-02")
def test_dashboard_role_gate():
    """DASH-03: Instructor dashboard is inaccessible to students."""
    ...
