---
phase: 2
slug: learning-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (backend) + Vitest (frontend) |
| **Config file** | backend/tests/conftest.py (existing, extend with new fixtures) |
| **Quick run command** | `cd backend && python -m pytest tests/test_courses.py tests/test_assignments.py tests/test_submissions.py tests/test_checkpoint_eval.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -q && cd ../frontend && npx vitest run` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_courses.py tests/test_assignments.py tests/test_submissions.py tests/test_checkpoint_eval.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -q && cd ../frontend && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | COUR-02 | unit | `pytest tests/test_courses.py::test_enrollment_code_format -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | COUR-03 | integration | `pytest tests/test_courses.py::test_enroll_success -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | COUR-03 | integration | `pytest tests/test_courses.py::test_enroll_invalid_code -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | DASH-03 | integration | `pytest tests/test_courses.py::test_dashboard_role_gate -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | COUR-01 | integration | `pytest tests/test_assignments.py::test_create_assignment -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | EDIT-01 | unit | `pytest tests/test_assignments.py::test_locked_params_in_response -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | COUR-04 | integration | `pytest tests/test_submissions.py::test_locked_param_mismatch -x` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | COUR-04 | integration | `pytest tests/test_submissions.py::test_highest_score_retention -x` | ❌ W0 | ⬜ pending |
| 02-03-03 | 03 | 2 | COUR-05 | unit | `pytest tests/test_checkpoint_eval.py::test_hard_gate_blocks_score -x` | ❌ W0 | ⬜ pending |
| 02-03-04 | 03 | 2 | COUR-05 | unit | `pytest tests/test_checkpoint_eval.py::test_partial_credit -x` | ❌ W0 | ⬜ pending |
| 02-03-05 | 03 | 2 | COUR-05 | unit | `pytest tests/test_checkpoint_eval.py::test_grade_published -x` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 2 | EDIT-01 | unit | `cd frontend && npx vitest run src/components/ConfigEditor` | ❌ W0 | ⬜ pending |
| 02-04-02 | 04 | 2 | EDIT-02 | unit | `cd frontend && npx vitest run src/components/ConfigEditor` | ❌ W0 | ⬜ pending |
| 02-05-01 | 05 | 2 | LAYT-02 | integration | `pytest tests/test_query.py::test_click_to_inspect_hit -x` | ❌ W0 | ⬜ pending |
| 02-05-02 | 05 | 2 | LAYT-02 | integration | `pytest tests/test_query.py::test_click_to_inspect_miss -x` | ❌ W0 | ⬜ pending |
| 02-06-01 | 06 | 3 | DASH-01 | integration | `pytest tests/test_submissions.py::test_leaderboard_order -x` | ❌ W0 | ⬜ pending |
| 02-06-02 | 06 | 3 | DASH-01 | integration | `pytest tests/test_submissions.py::test_leaderboard_anonymity -x` | ❌ W0 | ⬜ pending |
| 02-06-03 | 06 | 3 | DASH-02 | unit | `cd frontend && npx vitest run src/components/RunComparison` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_courses.py` — stubs for COUR-01, COUR-02, COUR-03, DASH-03
- [ ] `backend/tests/test_assignments.py` — stubs for COUR-01, EDIT-01
- [ ] `backend/tests/test_submissions.py` — stubs for COUR-04, DASH-01
- [ ] `backend/tests/test_checkpoint_eval.py` — stubs for COUR-05
- [ ] `backend/tests/test_query.py` — stubs for LAYT-02 (subprocess mocked)
- [ ] `frontend/src/components/ConfigEditor/ConfigEditor.test.tsx` — stubs for EDIT-01, EDIT-02
- [ ] `frontend/src/components/RunComparison/RunComparison.test.tsx` — stubs for DASH-02
- [ ] Alembic migration `0003_courses_assignments_submissions.py` — required before any table-hitting tests
- [ ] New ORM models registered in `backend/app/models/__init__.py`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| VNC session loads correct ODB file for stage | LAYT-02 | Requires running ORFS container | Open VNC tab after a completed run; verify design loads for each stage |
| Grade WebSocket push reaches browser terminal | COUR-05 | Requires live WebSocket client | Submit a run for grading; confirm grade result appears in frontend without page refresh |
| Instructor leaderboard view shows all students | DASH-03 | Requires multi-user session | Log in as instructor; verify class-wide dashboard shows all enrolled students' submissions |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
