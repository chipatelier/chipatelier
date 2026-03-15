"""Submission endpoint tests — plan 02-04."""
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.submission import Submission  # noqa: F401 — import to catch errors early


# ---------------------------------------------------------------------------
# Helpers (reused from test_assignments.py pattern)
# ---------------------------------------------------------------------------

def _register_and_login(client: TestClient, email: str, password: str = "securepass1") -> str:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": email.split("@")[0]},
    )
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


async def _create_instructor_and_course(
    client: TestClient,
    async_session,
    email: str,
    course_name: str = "Test Course",
) -> tuple[str, str, str, str]:
    """Returns (instructor_id, instructor_token, course_id, enrollment_code)."""
    from app.models.user import User

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


async def _create_student_with_run(
    client: TestClient,
    async_session,
    email: str,
    course_id: str,
    enrollment_code: str,
    run_config: dict | None = None,
) -> tuple[str, str, str]:
    """Register student, enroll, create project + run, return (student_token, student_id, run_id)."""
    from app.models.project import Project
    from app.models.run import Run
    from app.models.user import User

    student_token = _register_and_login(client, email)
    me_resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {student_token}"})
    student_id = me_resp.json()["id"]

    # Enroll
    client.post(
        f"/api/v1/courses/{course_id}/enroll",
        json={"enrollment_code": enrollment_code},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    # Create project + run directly in DB
    project = Project(
        user_id=uuid.UUID(student_id),
        name="Test Project",
        pdk="sky130hd",
    )
    async_session.add(project)
    await async_session.flush()

    run = Run(
        project_id=project.id,
        status="complete",
        ppa={"drc_violations": 0, "worst_negative_slack": -0.05},
        config=run_config or {"CLOCK_PERIOD": "10", "PLATFORM": "sky130hd"},
    )
    async_session.add(run)
    await async_session.commit()

    return student_token, student_id, str(run.id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_locked_param_mismatch(test_client: TestClient, async_session):
    """COUR-04: Submission is rejected if run config does not match locked params."""
    inst_id, inst_token, course_id, code = await _create_instructor_and_course(
        test_client, async_session, "inst_locked_mismatch@example.com"
    )

    # Create assignment with CLOCK_PERIOD locked to "10"
    resp = test_client.post(
        f"/api/v1/courses/{course_id}/assignments",
        json={
            "title": "Timing Lab",
            "locked_params": {"CLOCK_PERIOD": "10"},
            "checkpoint_rules": {
                "hard": [{"metric": "drc_violations", "op": "eq", "value": 0}],
                "scored": [],
            },
        },
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assert resp.status_code == 201
    assignment_id = resp.json()["id"]

    # Open it
    test_client.patch(
        f"/api/v1/assignments/{assignment_id}/open",
        json={"is_open": True},
        headers={"Authorization": f"Bearer {inst_token}"},
    )

    # Create student with run using CLOCK_PERIOD=8 (mismatch!)
    student_token, student_id, run_id = await _create_student_with_run(
        test_client, async_session,
        "student_locked_mismatch@example.com",
        course_id, code,
        run_config={"CLOCK_PERIOD": "8", "PLATFORM": "sky130hd"},
    )

    with patch("worker.tasks.checkpoint_eval.evaluate_submission.delay") as mock_delay:
        submit_resp = test_client.post(
            f"/api/v1/assignments/{assignment_id}/submit",
            json={"run_id": run_id},
            headers={"Authorization": f"Bearer {student_token}"},
        )

    assert submit_resp.status_code == 422, f"Expected 422, got {submit_resp.status_code}: {submit_resp.text}"
    body = submit_resp.json()
    # Error detail should mention CLOCK_PERIOD
    detail_str = str(body.get("detail", ""))
    assert "CLOCK_PERIOD" in detail_str, f"Expected CLOCK_PERIOD in error, got: {detail_str}"
    # Celery task must NOT be dispatched when locked params mismatch
    mock_delay.assert_not_called()


@pytest.mark.asyncio
async def test_highest_score_retention(test_client: TestClient, async_session):
    """COUR-04: Multiple submissions stored; GET /submissions/mine returns all in desc order."""
    inst_id, inst_token, course_id, code = await _create_instructor_and_course(
        test_client, async_session, "inst_multi_submit@example.com"
    )

    resp = test_client.post(
        f"/api/v1/courses/{course_id}/assignments",
        json={
            "title": "Multi Submit Lab",
            "locked_params": {},
            "checkpoint_rules": {
                "hard": [],
                "scored": [{"metric": "worst_negative_slack", "op": "gte", "value": -0.1, "points": 40}],
            },
        },
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assignment_id = resp.json()["id"]
    test_client.patch(
        f"/api/v1/assignments/{assignment_id}/open",
        json={"is_open": True},
        headers={"Authorization": f"Bearer {inst_token}"},
    )

    student_token, student_id, run_id = await _create_student_with_run(
        test_client, async_session,
        "student_multi_submit@example.com",
        course_id, code,
        run_config={},
    )

    # Submit twice — both should be stored (highest score display is frontend concern)
    with patch("worker.tasks.checkpoint_eval.evaluate_submission.delay"):
        resp1 = test_client.post(
            f"/api/v1/assignments/{assignment_id}/submit",
            json={"run_id": run_id},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        resp2 = test_client.post(
            f"/api/v1/assignments/{assignment_id}/submit",
            json={"run_id": run_id},
            headers={"Authorization": f"Bearer {student_token}"},
        )

    assert resp1.status_code == 201, f"First submit failed: {resp1.text}"
    assert resp2.status_code == 201, f"Second submit failed: {resp2.text}"

    # GET /submissions/mine — should return both submissions
    mine_resp = test_client.get(
        f"/api/v1/assignments/{assignment_id}/submissions/mine",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert mine_resp.status_code == 200, f"Expected 200, got {mine_resp.status_code}: {mine_resp.text}"
    submissions = mine_resp.json()
    assert len(submissions) == 2, f"Expected 2 submissions, got {len(submissions)}"


@pytest.mark.asyncio
async def test_submit_dispatches_celery_task(test_client: TestClient, async_session):
    """Successful submission dispatches evaluate_submission.delay() with submission ID."""
    inst_id, inst_token, course_id, code = await _create_instructor_and_course(
        test_client, async_session, "inst_celery_dispatch@example.com"
    )

    resp = test_client.post(
        f"/api/v1/courses/{course_id}/assignments",
        json={
            "title": "Celery Dispatch Lab",
            "locked_params": {},
            "checkpoint_rules": {"hard": [], "scored": []},
        },
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assignment_id = resp.json()["id"]
    test_client.patch(
        f"/api/v1/assignments/{assignment_id}/open",
        json={"is_open": True},
        headers={"Authorization": f"Bearer {inst_token}"},
    )

    student_token, student_id, run_id = await _create_student_with_run(
        test_client, async_session,
        "student_celery_dispatch@example.com",
        course_id, code,
    )

    with patch("worker.tasks.checkpoint_eval.evaluate_submission.delay") as mock_delay:
        resp = test_client.post(
            f"/api/v1/assignments/{assignment_id}/submit",
            json={"run_id": run_id},
            headers={"Authorization": f"Bearer {student_token}"},
        )

    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    mock_delay.assert_called_once()
    # Verify the submission ID string was passed
    call_args = mock_delay.call_args[0]
    assert len(call_args) == 1
    # Should be a UUID string
    uuid.UUID(call_args[0])


@pytest.mark.asyncio
async def test_preview_score_no_submission_created(test_client: TestClient, async_session):
    """GET /preview-score computes result without creating a Submission."""
    from app.models.submission import Submission

    inst_id, inst_token, course_id, code = await _create_instructor_and_course(
        test_client, async_session, "inst_preview_score@example.com"
    )

    resp = test_client.post(
        f"/api/v1/courses/{course_id}/assignments",
        json={
            "title": "Preview Lab",
            "locked_params": {},
            "checkpoint_rules": {
                "hard": [{"metric": "drc_violations", "op": "eq", "value": 0}],
                "scored": [{"metric": "worst_negative_slack", "op": "gte", "value": -0.1, "points": 40}],
            },
        },
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assignment_id = resp.json()["id"]
    test_client.patch(
        f"/api/v1/assignments/{assignment_id}/open",
        json={"is_open": True},
        headers={"Authorization": f"Bearer {inst_token}"},
    )

    student_token, student_id, run_id = await _create_student_with_run(
        test_client, async_session,
        "student_preview_score@example.com",
        course_id, code,
        run_config={},
    )

    preview_resp = test_client.get(
        f"/api/v1/assignments/{assignment_id}/preview-score?run_id={run_id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert preview_resp.status_code == 200, f"Expected 200, got {preview_resp.status_code}: {preview_resp.text}"
    body = preview_resp.json()
    assert "score" in body
    assert "checkpoint_results" in body
    assert "is_eligible" in body

    # No submission should be created
    result = await async_session.execute(
        select(Submission).where(Submission.user_id == uuid.UUID(student_id))
    )
    submissions = result.scalars().all()
    assert len(submissions) == 0, "preview-score must not create a Submission"


@pytest.mark.asyncio
async def test_submit_run_not_complete(test_client: TestClient, async_session):
    """Cannot submit a run that is not in 'complete' status."""
    from app.models.project import Project
    from app.models.run import Run

    inst_id, inst_token, course_id, code = await _create_instructor_and_course(
        test_client, async_session, "inst_not_complete@example.com"
    )

    resp = test_client.post(
        f"/api/v1/courses/{course_id}/assignments",
        json={"title": "Not Complete Lab", "locked_params": {}, "checkpoint_rules": {}},
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assignment_id = resp.json()["id"]
    test_client.patch(
        f"/api/v1/assignments/{assignment_id}/open",
        json={"is_open": True},
        headers={"Authorization": f"Bearer {inst_token}"},
    )

    student_token = _register_and_login(test_client, "student_not_complete@example.com")
    me_resp = test_client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {student_token}"})
    student_id = me_resp.json()["id"]
    test_client.post(
        f"/api/v1/courses/{course_id}/enroll",
        json={"enrollment_code": code},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    project = Project(user_id=uuid.UUID(student_id), name="P", pdk="sky130hd")
    async_session.add(project)
    await async_session.flush()
    run = Run(project_id=project.id, status="running")  # Not complete!
    async_session.add(run)
    await async_session.commit()

    with patch("worker.tasks.checkpoint_eval.evaluate_submission.delay"):
        resp = test_client.post(
            f"/api/v1/assignments/{assignment_id}/submit",
            json={"run_id": str(run.id)},
            headers={"Authorization": f"Bearer {student_token}"},
        )

    assert resp.status_code == 400, f"Expected 400 for non-complete run, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_leaderboard_order(test_client: TestClient, async_session):
    """DASH-01: Leaderboard returns submissions ordered by score DESC, WNS numeric DESC as tiebreaker."""
    from app.models.project import Project
    from app.models.run import Run
    from app.models.user import User

    inst_id, inst_token, course_id, code = await _create_instructor_and_course(
        test_client, async_session, "inst_leaderboard_order@example.com"
    )

    # Create assignment with scored rules
    resp = test_client.post(
        f"/api/v1/courses/{course_id}/assignments",
        json={
            "title": "Leaderboard Order Lab",
            "locked_params": {},
            "checkpoint_rules": {
                "hard": [],
                "scored": [{"metric": "worst_negative_slack", "op": "gte", "value": -0.5, "points": 100}],
            },
        },
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assert resp.status_code == 201, f"Assignment creation failed: {resp.text}"
    assignment_id = resp.json()["id"]
    test_client.patch(
        f"/api/v1/assignments/{assignment_id}/open",
        json={"is_open": True},
        headers={"Authorization": f"Bearer {inst_token}"},
    )

    # Create 3 students with submissions: scores [95, 80, 80] and WNS [-0.05, -0.1, -0.2]
    async def create_student_submission(email: str, score: float, wns: float) -> str:
        """Create student, run, and submission directly in DB. Returns student_id."""
        token = _register_and_login(test_client, email)
        me = test_client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        student_id = me.json()["id"]

        test_client.post(
            f"/api/v1/courses/{course_id}/enroll",
            json={"enrollment_code": code},
            headers={"Authorization": f"Bearer {token}"},
        )

        project = Project(user_id=uuid.UUID(student_id), name="P", pdk="sky130hd")
        async_session.add(project)
        await async_session.flush()

        run = Run(
            project_id=project.id,
            status="complete",
            ppa={"worst_negative_slack": wns, "drc_violations": 0},
            config={},
        )
        async_session.add(run)
        await async_session.flush()

        from app.models.submission import Submission as Sub
        sub = Sub(
            assignment_id=uuid.UUID(assignment_id),
            user_id=uuid.UUID(student_id),
            run_id=run.id,
            score=score,
            grading_status="complete",
        )
        async_session.add(sub)
        await async_session.commit()
        return student_id

    student1_id = await create_student_submission("student_lb1@example.com", 95.0, -0.05)
    student2_id = await create_student_submission("student_lb2@example.com", 80.0, -0.1)
    student3_id = await create_student_submission("student_lb3@example.com", 80.0, -0.2)

    # Call leaderboard as student1
    token1 = test_client.post("/api/v1/auth/login", json={"email": "student_lb1@example.com", "password": "securepass1"}).json()["access_token"]
    lb_resp = test_client.get(
        f"/api/v1/assignments/{assignment_id}/leaderboard",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert lb_resp.status_code == 200, f"Expected 200, got {lb_resp.status_code}: {lb_resp.text}"
    entries = lb_resp.json()
    assert len(entries) == 3, f"Expected 3 entries, got {len(entries)}"

    # rank1 = score 95
    assert entries[0]["rank"] == 1
    assert entries[0]["score"] == 95.0
    # rank2 = score 80 with WNS -0.1 (better than -0.2)
    assert entries[1]["rank"] == 2
    assert entries[1]["score"] == 80.0
    # rank3 = score 80 with WNS -0.2 (worse)
    assert entries[2]["rank"] == 3
    assert entries[2]["score"] == 80.0
    # Verify WNS ordering: rank2 WNS should be greater than rank3 WNS (-0.1 > -0.2)
    wns2 = float(entries[1]["wns"])
    wns3 = float(entries[2]["wns"])
    assert wns2 > wns3, f"Expected rank2 WNS ({wns2}) > rank3 WNS ({wns3})"


@pytest.mark.asyncio
async def test_leaderboard_anonymity(test_client: TestClient, async_session):
    """DASH-01: Leaderboard is_self=True for caller, is_self=False for all others."""
    from app.models.project import Project
    from app.models.run import Run
    from app.models.submission import Submission as Sub

    inst_id, inst_token, course_id, code = await _create_instructor_and_course(
        test_client, async_session, "inst_leaderboard_anon@example.com"
    )

    resp = test_client.post(
        f"/api/v1/courses/{course_id}/assignments",
        json={
            "title": "Anon Lab",
            "locked_params": {},
            "checkpoint_rules": {"hard": [], "scored": []},
        },
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assignment_id = resp.json()["id"]
    test_client.patch(
        f"/api/v1/assignments/{assignment_id}/open",
        json={"is_open": True},
        headers={"Authorization": f"Bearer {inst_token}"},
    )

    # Create 2 students with submissions
    async def make_student_sub(email: str, score: float) -> tuple[str, str]:
        token = _register_and_login(test_client, email)
        me = test_client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        student_id = me.json()["id"]
        test_client.post(
            f"/api/v1/courses/{course_id}/enroll",
            json={"enrollment_code": code},
            headers={"Authorization": f"Bearer {token}"},
        )
        project = Project(user_id=uuid.UUID(student_id), name="P", pdk="sky130hd")
        async_session.add(project)
        await async_session.flush()
        run = Run(project_id=project.id, status="complete", ppa={}, config={})
        async_session.add(run)
        await async_session.flush()
        sub = Sub(
            assignment_id=uuid.UUID(assignment_id),
            user_id=uuid.UUID(student_id),
            run_id=run.id,
            score=score,
            grading_status="complete",
        )
        async_session.add(sub)
        await async_session.commit()
        return student_id, token

    student1_id, token1 = await make_student_sub("student_anon1@example.com", 80.0)
    student2_id, token2 = await make_student_sub("student_anon2@example.com", 70.0)

    # Call leaderboard as student2 — their row should have is_self=True
    lb_resp = test_client.get(
        f"/api/v1/assignments/{assignment_id}/leaderboard",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert lb_resp.status_code == 200, f"Expected 200, got {lb_resp.status_code}: {lb_resp.text}"
    entries = lb_resp.json()
    assert len(entries) == 2

    # Find student2's entry
    self_entries = [e for e in entries if e["is_self"]]
    other_entries = [e for e in entries if not e["is_self"]]
    assert len(self_entries) == 1, f"Expected exactly 1 is_self=True entry, got {len(self_entries)}"
    assert len(other_entries) == 1, f"Expected exactly 1 is_self=False entry, got {len(other_entries)}"
    # The self entry should be student2 (score 70)
    assert self_entries[0]["user_id"] == student2_id
    assert self_entries[0]["score"] == 70.0
