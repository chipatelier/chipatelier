"""Assignment endpoint tests — plan 02-02."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.models.assignment import Assignment  # noqa: F401 — import to catch errors early


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(client: TestClient, email: str, password: str = "securepass1") -> str:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": email.split("@")[0]},
    )
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


async def _create_instructor_and_course(client: TestClient, async_session, email: str, course_name: str = "Test Course") -> tuple[str, str, str, str]:
    """Returns (instructor_id, instructor_token, course_id, enrollment_code)."""
    from app.models.user import User
    from sqlalchemy import select

    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "display_name": email.split("@")[0]},
    )
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "securepass1"})
    token = login_resp.json()["access_token"]
    me_resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    user_id = me_resp.json()["id"]

    # Promote to instructor
    result = await async_session.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one()
    user.role = "instructor"
    await async_session.commit()

    # Create course
    course_resp = client.post(
        "/api/v1/courses",
        json={"name": course_name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert course_resp.status_code == 201, f"Course creation failed: {course_resp.text}"
    course_data = course_resp.json()
    return user_id, token, course_data["id"], course_data["enrollment_code"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_assignment(test_client: TestClient, async_session):
    """COUR-01: Instructor can create an assignment linked to a course."""
    inst_id, inst_token, course_id, code = await _create_instructor_and_course(
        test_client, async_session, "inst_assignment_create@example.com"
    )

    resp = test_client.post(
        f"/api/v1/courses/{course_id}/assignments",
        json={
            "title": "Lab 1 — Floorplan Basics",
            "pdk": "sky130hd",
            "target_stage": "route",
            "locked_params": {"CLOCK_PERIOD": "10", "PLATFORM": "sky130hd"},
            "editable_params": ["CORE_UTILIZATION", "PLACE_DENSITY"],
            "checkpoint_rules": {
                "hard": [{"metric": "drc_violations", "op": "eq", "value": 0}],
                "scored": [{"metric": "worst_negative_slack", "op": "gte", "value": -0.1, "points": 40}],
            },
        },
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["title"] == "Lab 1 — Floorplan Basics"
    assert data["course_id"] == course_id
    assert data["is_open"] == False  # default hidden
    assert "id" in data


@pytest.mark.asyncio
async def test_locked_params_in_response(test_client: TestClient, async_session):
    """EDIT-01: locked_params appear in assignment response and values are strings."""
    inst_id, inst_token, course_id, code = await _create_instructor_and_course(
        test_client, async_session, "inst_locked_params@example.com"
    )

    resp = test_client.post(
        f"/api/v1/courses/{course_id}/assignments",
        json={
            "title": "Timing Lab",
            # Pass as int — should be coerced to str by schema validator
            "locked_params": {"CLOCK_PERIOD": 10},
            "editable_params": ["CORE_UTILIZATION"],
        },
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    data = resp.json()
    # locked_params values must be strings
    assert data["locked_params"]["CLOCK_PERIOD"] == "10", \
        f"Expected '10' (str), got {data['locked_params']['CLOCK_PERIOD']!r}"


@pytest.mark.asyncio
async def test_student_cannot_create_assignment(test_client: TestClient, async_session):
    """COUR-01: Non-instructors receive 403 when creating assignments."""
    inst_id, inst_token, course_id, code = await _create_instructor_and_course(
        test_client, async_session, "inst_for_student_gate@example.com"
    )

    student_token = _register_and_login(test_client, "student_assign_gate@example.com")
    resp = test_client.post(
        f"/api/v1/courses/{course_id}/assignments",
        json={"title": "Sneaky Assignment"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_toggle_assignment_open(test_client: TestClient, async_session):
    """Assignment is hidden by default; PATCH /assignments/{id}/open toggles it."""
    inst_id, inst_token, course_id, code = await _create_instructor_and_course(
        test_client, async_session, "inst_toggle_open@example.com"
    )

    create_resp = test_client.post(
        f"/api/v1/courses/{course_id}/assignments",
        json={"title": "Toggle Lab"},
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assert create_resp.status_code == 201
    assignment_id = create_resp.json()["id"]
    assert create_resp.json()["is_open"] == False

    # Open it
    toggle_resp = test_client.patch(
        f"/api/v1/assignments/{assignment_id}/open",
        json={"is_open": True},
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assert toggle_resp.status_code == 200, f"Expected 200, got {toggle_resp.status_code}: {toggle_resp.text}"
    assert toggle_resp.json()["is_open"] == True

    # Close it again
    toggle_resp2 = test_client.patch(
        f"/api/v1/assignments/{assignment_id}/open",
        json={"is_open": False},
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assert toggle_resp2.status_code == 200
    assert toggle_resp2.json()["is_open"] == False


@pytest.mark.asyncio
async def test_list_assignments_student_sees_open_only(test_client: TestClient, async_session):
    """Students only see assignments where is_open=True."""
    inst_id, inst_token, course_id, code = await _create_instructor_and_course(
        test_client, async_session, "inst_list_assignments@example.com"
    )

    # Create two assignments
    a1 = test_client.post(
        f"/api/v1/courses/{course_id}/assignments",
        json={"title": "Hidden Lab"},
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    a2 = test_client.post(
        f"/api/v1/courses/{course_id}/assignments",
        json={"title": "Open Lab"},
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    a2_id = a2.json()["id"]

    # Open the second one
    test_client.patch(
        f"/api/v1/assignments/{a2_id}/open",
        json={"is_open": True},
        headers={"Authorization": f"Bearer {inst_token}"},
    )

    # Student enrolls
    student_token = _register_and_login(test_client, "student_list_assign@example.com")
    test_client.post(
        f"/api/v1/courses/{course_id}/enroll",
        json={"enrollment_code": code},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    # Student lists assignments — should only see Open Lab
    list_resp = test_client.get(
        f"/api/v1/courses/{course_id}/assignments",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert list_resp.status_code == 200, f"Expected 200, got {list_resp.status_code}: {list_resp.text}"
    titles = [a["title"] for a in list_resp.json()]
    assert "Open Lab" in titles
    assert "Hidden Lab" not in titles


@pytest.mark.asyncio
async def test_list_assignments_instructor_sees_all(test_client: TestClient, async_session):
    """Instructors see all assignments (open and hidden)."""
    inst_id, inst_token, course_id, code = await _create_instructor_and_course(
        test_client, async_session, "inst_list_all_assigns@example.com"
    )

    test_client.post(
        f"/api/v1/courses/{course_id}/assignments",
        json={"title": "Draft Lab"},
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    test_client.post(
        f"/api/v1/courses/{course_id}/assignments",
        json={"title": "Published Lab"},
        headers={"Authorization": f"Bearer {inst_token}"},
    )

    list_resp = test_client.get(
        f"/api/v1/courses/{course_id}/assignments",
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assert list_resp.status_code == 200
    titles = [a["title"] for a in list_resp.json()]
    assert "Draft Lab" in titles
    assert "Published Lab" in titles
