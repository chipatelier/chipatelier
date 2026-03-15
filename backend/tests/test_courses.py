"""Course and enrollment endpoint tests — plan 02-02."""
import re
import uuid

import pytest
from fastapi.testclient import TestClient

from app.models.course import Course  # noqa: F401 — import to catch errors early
from app.models.enrollment import CourseEnrollment  # noqa: F401


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(client: TestClient, email: str, password: str = "securepass1") -> str:
    """Register a student user and return access token."""
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": email.split("@")[0]},
    )
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


def _make_instructor(client: TestClient, email: str, password: str = "securepass1") -> tuple[str, str]:
    """Register + login an instructor. Returns (user_id, access_token).

    We directly update the DB role via the admin users endpoint or DB.
    Since we don't have an admin endpoint here, we patch via the DB using
    the async_session fixture approach — but test_client already wraps that.

    Instead: use the /api/v1/users/me PATCH or just inject role via DB.
    """
    from app.main import app
    from app.core.database import get_db
    from sqlalchemy import select
    from app.models.user import User

    # Register
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": email.split("@")[0]},
    )
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login_resp.json()["access_token"]
    user_id = login_resp.json().get("user_id")  # might not exist — get from /me
    me_resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    user_id = me_resp.json()["id"]
    return user_id, token


# ---------------------------------------------------------------------------
# Unit: enrollment code format
# ---------------------------------------------------------------------------

def test_enrollment_code_format():
    """COUR-02: Enrollment code must match VLSI-YYYY-XXXX format (safe alphabet)."""
    from app.api.routes.courses import generate_enrollment_code

    pattern = re.compile(r"^VLSI-\d{4}-[A-HJ-NP-Z1-9]{4}$")
    for _ in range(100):
        code = generate_enrollment_code()
        assert pattern.match(code), f"Code '{code}' does not match pattern"


# ---------------------------------------------------------------------------
# API: create course — instructor gate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_course_instructor_only(test_client: TestClient, async_session):
    """COUR-02: Only users with role=instructor can create a course (student → 403)."""
    # Register + login as student (default role)
    student_token = _register_and_login(test_client, "student_course_gate@example.com")

    resp = test_client.post(
        "/api/v1/courses",
        json={"name": "VLSI 101", "term": "Fall 2026"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_create_course_as_instructor(test_client: TestClient, async_session):
    """COUR-02: Instructor can create a course; response includes enrollment_code."""
    from app.models.user import User
    from sqlalchemy import select

    # Register as student first
    user_id, token = _make_instructor(test_client, "instructor_create@example.com")

    # Promote to instructor in DB
    result = await async_session.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one()
    user.role = "instructor"
    await async_session.commit()

    # Create course
    resp = test_client.post(
        "/api/v1/courses",
        json={"name": "Digital Design", "term": "Spring 2026"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["name"] == "Digital Design"
    assert re.match(r"^VLSI-\d{4}-[A-HJ-NP-Z1-9]{4}$", data["enrollment_code"]), \
        f"Bad enrollment_code: {data['enrollment_code']}"


# ---------------------------------------------------------------------------
# API: enrollment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enroll_success(test_client: TestClient, async_session):
    """COUR-03: Student can enroll with a valid enrollment code."""
    from app.models.user import User
    from sqlalchemy import select

    # Create instructor
    inst_id, inst_token = _make_instructor(test_client, "instructor_enroll_ok@example.com")
    result = await async_session.execute(select(User).where(User.id == uuid.UUID(inst_id)))
    user = result.scalar_one()
    user.role = "instructor"
    await async_session.commit()

    # Create course
    course_resp = test_client.post(
        "/api/v1/courses",
        json={"name": "Enrollment Test Course"},
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assert course_resp.status_code == 201
    course_data = course_resp.json()
    course_id = course_data["id"]
    enrollment_code = course_data["enrollment_code"]

    # Student enrolls
    student_token = _register_and_login(test_client, "student_enroll_ok@example.com")
    resp = test_client.post(
        f"/api/v1/courses/{course_id}/enroll",
        json={"enrollment_code": enrollment_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["course_id"] == course_id
    assert data["course_name"] == "Enrollment Test Course"


@pytest.mark.asyncio
async def test_enroll_invalid_code(test_client: TestClient, async_session):
    """COUR-03: Enrollment with unknown code returns 404."""
    from app.models.user import User
    from sqlalchemy import select

    # Need a course to exist first (so route can look up by code)
    inst_id, inst_token = _make_instructor(test_client, "instructor_invalid_code@example.com")
    result = await async_session.execute(select(User).where(User.id == uuid.UUID(inst_id)))
    user = result.scalar_one()
    user.role = "instructor"
    await async_session.commit()

    course_resp = test_client.post(
        "/api/v1/courses",
        json={"name": "Invalid Code Test"},
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assert course_resp.status_code == 201
    course_id = course_resp.json()["id"]

    student_token = _register_and_login(test_client, "student_invalid@example.com")
    resp = test_client.post(
        f"/api/v1/courses/{course_id}/enroll",
        json={"enrollment_code": "VLSI-9999-ZZZZ"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_enroll_duplicate_returns_409(test_client: TestClient, async_session):
    """COUR-03: Duplicate enrollment returns 409 Conflict."""
    from app.models.user import User
    from sqlalchemy import select

    inst_id, inst_token = _make_instructor(test_client, "instructor_dup@example.com")
    result = await async_session.execute(select(User).where(User.id == uuid.UUID(inst_id)))
    user = result.scalar_one()
    user.role = "instructor"
    await async_session.commit()

    course_resp = test_client.post(
        "/api/v1/courses",
        json={"name": "Duplicate Enroll Test"},
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    course_id = course_resp.json()["id"]
    code = course_resp.json()["enrollment_code"]

    student_token = _register_and_login(test_client, "student_dup@example.com")
    # First enrollment
    resp1 = test_client.post(
        f"/api/v1/courses/{course_id}/enroll",
        json={"enrollment_code": code},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp1.status_code == 200
    # Second enrollment — should return 409
    resp2 = test_client.post(
        f"/api/v1/courses/{course_id}/enroll",
        json={"enrollment_code": code},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp2.status_code == 409, f"Expected 409, got {resp2.status_code}: {resp2.text}"


@pytest.mark.asyncio
async def test_dashboard_role_gate(test_client: TestClient, async_session):
    """DASH-03: Instructor dashboard (course creation) is inaccessible to students."""
    student_token = _register_and_login(test_client, "student_dash_gate@example.com")
    resp = test_client.post(
        "/api/v1/courses",
        json={"name": "Should Fail"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_dashboard_endpoint_role_gate(test_client: TestClient, async_session):
    """DASH-03: GET /courses/{id}/dashboard returns 403 for student role."""
    from app.models.user import User
    from sqlalchemy import select

    # Create instructor + course
    inst_id, inst_token = _make_instructor(test_client, "instructor_dashboard_gate@example.com")
    result = await async_session.execute(select(User).where(User.id == uuid.UUID(inst_id)))
    user = result.scalar_one()
    user.role = "instructor"
    await async_session.commit()

    course_resp = test_client.post(
        "/api/v1/courses",
        json={"name": "Dashboard Gate Course"},
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assert course_resp.status_code == 201
    course_id = course_resp.json()["id"]

    # Student tries to access dashboard — should get 403
    student_token = _register_and_login(test_client, "student_dashboard_gate@example.com")
    resp = test_client.get(
        f"/api/v1/courses/{course_id}/dashboard",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 403, f"Expected 403 for student accessing dashboard, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_dashboard_returns_student_progress(test_client: TestClient, async_session):
    """DASH-03: GET /courses/{id}/dashboard returns students[] with progress info for instructor."""
    from app.models.user import User
    from sqlalchemy import select

    inst_id, inst_token = _make_instructor(test_client, "instructor_dash_progress@example.com")
    result = await async_session.execute(select(User).where(User.id == uuid.UUID(inst_id)))
    user = result.scalar_one()
    user.role = "instructor"
    await async_session.commit()

    course_resp = test_client.post(
        "/api/v1/courses",
        json={"name": "Progress Dashboard Course"},
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assert course_resp.status_code == 201
    course_id = course_resp.json()["id"]
    enrollment_code = course_resp.json()["enrollment_code"]

    # Enroll a student
    student_token = _register_and_login(test_client, "student_progress@example.com")
    test_client.post(
        f"/api/v1/courses/{course_id}/enroll",
        json={"enrollment_code": enrollment_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    # Instructor accesses dashboard
    resp = test_client.get(
        f"/api/v1/courses/{course_id}/dashboard",
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "students" in data, f"Response missing 'students' key: {data}"
    assert "queue_info" in data, f"Response missing 'queue_info' key: {data}"
    assert len(data["students"]) == 1, f"Expected 1 student, got {len(data['students'])}"
    student_entry = data["students"][0]
    assert "display_name" in student_entry
    assert "run_count" in student_entry
    assert "submission_status" in student_entry
