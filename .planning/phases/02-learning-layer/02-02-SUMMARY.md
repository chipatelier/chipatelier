---
phase: 02-learning-layer
plan: "02"
subsystem: api
tags: [fastapi, pydantic, sqlalchemy, courses, assignments, enrollment, role-based-access]

# Dependency graph
requires:
  - phase: 02-01
    provides: "Course, CourseEnrollment, Assignment, Submission ORM models + migration 0003"
  - phase: 01-core-flow
    provides: "get_current_user dep, require_role dep, User model with role field, async session fixtures"

provides:
  - "POST /api/v1/courses — instructor creates course with VLSI-YYYY-XXXX enrollment code"
  - "GET /api/v1/courses — list courses for current user (taught/enrolled)"
  - "POST /api/v1/courses/{id}/enroll — student enrollment via code (409 on dup, 404 on bad code)"
  - "POST /api/v1/courses/{id}/assignments — instructor creates assignment (is_open=False default)"
  - "GET /api/v1/courses/{id}/assignments — list (students see open only, instructors see all)"
  - "PATCH /api/v1/assignments/{id}/open — toggle is_open boolean (instructor-only)"
  - "CourseCreate, CourseResponse, EnrollRequest, EnrollResponse Pydantic schemas"
  - "AssignmentCreate, AssignmentResponse, AssignmentOpenToggle Pydantic schemas"

affects:
  - "02-03 — leaderboard will JOIN against courses/assignments to scope rankings"
  - "Phase 3 checkpoint_eval — reads assignments.checkpoint_rules and assignments.locked_params"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Enrollment code: secrets.choice + safe alphabet (no O/I/0) + VLSI-YYYY-XXXX format"
    - "Collision-safe DB unique code: 10-attempt retry loop + HTTP 500 on exhaustion"
    - "Role gate helper: _require_instructor() used inline per route (not as FastAPI Depends)"
    - "Course ownership gate: _require_course_instructor() verifies instructor_id match"
    - "field_validator mode=before on locked_params coerces dict values to str (both Create + Response)"
    - "Student-filtered queries: JOIN CourseEnrollment WHERE user_id + filter is_open=True"

key-files:
  created:
    - backend/app/schemas/courses.py
    - backend/app/schemas/assignments.py
    - backend/app/api/routes/courses.py
    - backend/app/api/routes/assignments.py
  modified:
    - backend/app/main.py
    - backend/tests/test_courses.py
    - backend/tests/test_assignments.py

key-decisions:
  - "Enrollment code collision check via SELECT before INSERT (not caught at IntegrityError) for cleaner retry loop semantics"
  - "Instructor gate uses helper function _require_instructor() not FastAPI Depends factory — matches existing codebase pattern from projects.py"
  - "Student list endpoint filters is_open=True; instructors see all (no separate instructor list endpoint)"
  - "locked_params coercion to str applied in BOTH AssignmentCreate and AssignmentResponse validators to prevent round-trip int/str mismatch"

patterns-established:
  - "Role gate pattern: _require_instructor(user) called inline at top of handler body"
  - "Ownership gate pattern: _require_course_instructor(course, user) called after fetching course"
  - "Enrollment code format: VLSI-{year}-{4-char safe-alphabet} validated by regex ^VLSI-\\d{4}-[A-HJ-NP-Z1-9]{4}$"

requirements-completed:
  - COUR-01
  - COUR-02
  - COUR-03

# Metrics
duration: 5min
completed: 2026-03-15
---

# Phase 2 Plan 02: Course and Assignment Backend Summary

**FastAPI course management API with enrollment-code-based enrollment, instructor role gates, and assignment CRUD with locked_params coercion and is_open visibility control**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T08:25:47Z
- **Completed:** 2026-03-15T08:30:52Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Course creation endpoint generates collision-safe enrollment codes (VLSI-YYYY-XXXX format, safe alphabet, 10-retry loop) with 403 gate for non-instructors
- Student enrollment endpoint with 404 on unknown code, 409 on duplicate enrollment, stored via CourseEnrollment ORM model
- Assignment CRUD with instructor-only creation, is_open=False default, toggle endpoint, and student-visible filtering (only open assignments)
- Pydantic schemas with field_validator coercing all locked_params values to str on both create and response paths
- 13 real tests replacing stubs: enrollment code regex validation, role gates, enrollment happy/sad/duplicate paths, assignment creation, locked_params coercion, toggle, and list filtering

## Task Commits

Each task was committed atomically:

1. **Task 1: Pydantic schemas for courses and assignments** - `4152336` (feat)
2. **Task 2: Course and assignment route files + router registration** - `1a573da` (feat)

**Plan metadata:** (pending docs commit)

## Files Created/Modified

- `backend/app/schemas/courses.py` — CourseCreate, CourseResponse, EnrollRequest, EnrollResponse
- `backend/app/schemas/assignments.py` — AssignmentCreate, AssignmentResponse, AssignmentOpenToggle with locked_params coercion
- `backend/app/api/routes/courses.py` — POST/GET /courses, POST /courses/{id}/enroll + generate_enrollment_code()
- `backend/app/api/routes/assignments.py` — POST/GET /courses/{id}/assignments, PATCH /assignments/{id}/open
- `backend/app/main.py` — registered courses_router and assignments_router under /api/v1
- `backend/tests/test_courses.py` — replaced 5 stubs with 6 real async tests
- `backend/tests/test_assignments.py` — replaced 2 stubs with 6 real async tests (+ 1 test_enrollment_code_format unit test)

## Decisions Made

- Enrollment code collision check uses SELECT before INSERT (not IntegrityError catch) for explicit 10-attempt retry semantics — more predictable than exception-driven retry
- Instructor gate uses `_require_instructor(user)` helper function called inline, not a FastAPI `Depends` factory — consistent with `_check_ownership` pattern in projects.py
- `locked_params` coercion to `str` applied in both `AssignmentCreate` and `AssignmentResponse` validators — prevents int/str round-trip mismatch if data enters DB as int

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing `prometheus-fastapi-instrumentator` package**
- **Found during:** Task 2 (running test suite)
- **Issue:** `prometheus_fastapi_instrumentator` not installed in system Python used by pytest, causing `ModuleNotFoundError` when importing `app.main`
- **Fix:** `pip install prometheus-fastapi-instrumentator` into the active Python environment
- **Files modified:** None (package install)
- **Verification:** All 13 tests pass; confirmed failure was pre-existing on stash check
- **Committed in:** Not committed (no pyproject.toml change needed — already declared as dependency)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Package install unblocked test execution. No scope creep.

## Issues Encountered

- `test_fair_queue.py` fails on collection due to `ModuleNotFoundError: No module named 'tasks'` in worker package — pre-existing issue not related to this plan, out of scope
- 6 pre-existing test failures in `test_tile_generator.py` and `test_vnc.py` — confirmed by stash check, unchanged by this plan

## Next Phase Readiness

- Course and enrollment system complete — students can enroll, instructors can create courses and assignments
- Plan 02-03 (leaderboard) can JOIN against `courses`, `course_enrollments`, and `assignments`
- `assignments.checkpoint_rules` and `assignments.locked_params` ready for Phase 3 checkpoint evaluation

---
*Phase: 02-learning-layer*
*Completed: 2026-03-15*
