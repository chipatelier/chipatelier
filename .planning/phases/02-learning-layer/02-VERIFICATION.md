---
phase: 02-learning-layer
verified: 2026-03-15T22:30:00Z
status: human_needed
score: 11/11 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 10/11
  gaps_closed:
    - "Leaderboard ORDER BY uses functional B-tree index idx_runs_wns_numeric at the DB level (SQL text expression)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "ConfigEditor form/raw toggle in running browser"
    expected: "Clicking Raw shows Monaco editor with config.mk syntax highlighting; clicking Form shows labeled inputs with range indicators"
    why_human: "Monaco editor rendering and syntax highlighting require a live browser — can only verify mocked version in tests"
  - test: "Click-to-inspect on a completed run layout PNG"
    expected: "Clicking a cell on the PNG opens InspectSidebar showing cell name, master type, and connected net names; clicking empty space shows 'No element at this location'"
    why_human: "Requires a live Docker environment with the ORFS image, MinIO with actual ODB file, and a running backend — subprocess integration cannot be verified without the full stack"
  - test: "Grade WebSocket push after submission"
    expected: "After submitting a run, an optimistic 'Submitted — grading in progress...' banner appears; when grade arrives via WebSocket, CheckpointCards switches to result mode showing per-criterion pass/fail"
    why_human: "Requires live Celery worker, Redis, and WebSocket connection — cannot verify end-to-end without the full stack"
---

# Phase 2: Learning Layer Verification Report

**Phase Goal:** Instructors can run a course on ChipAtelier — creating assignments with locked parameters and checkpoint rules — and students can submit for auto-graded scores with leaderboard ranking
**Verified:** 2026-03-15T22:30:00Z
**Status:** human_needed — all automated checks pass; 3 items require live stack testing
**Re-verification:** Yes — after gap closure (plan 02-07 closed the single DASH-01 leaderboard gap)

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Instructor can create a course with VLSI-YYYY-XXXX enrollment code | VERIFIED | `courses.py` generate_enrollment_code() + collision retry; `test_enrollment_code_format` validates regex |
| 2  | Student can enroll via enrollment code; duplicate returns 409 | VERIFIED | `courses.py` POST /courses/{id}/enroll checks duplicate and returns 409 |
| 3  | Instructor can create assignment with locked_params, editable_params, checkpoint_rules | VERIFIED | `assignments.py` POST /courses/{id}/assignments; AssignmentCreate schema with field_validator coercing locked_params to str |
| 4  | Assignments hidden by default (is_open=False); instructor can toggle open | VERIFIED | `assignments.py` PATCH /assignments/{id}/open; default is_open=False in ORM model |
| 5  | Student can submit a run; locked param mismatch returns 422 | VERIFIED | `submissions.py` _validate_locked_params(); dispatches evaluate_submission.delay() inside handler body |
| 6  | Checkpoint evaluator blocks score on hard gate failure; partial credit applied correctly | VERIFIED | `checkpoint_eval.py` evaluate_checkpoint_rules() — pure function, tested in test_checkpoint_eval.py |
| 7  | Grade result pushed to browser via Redis pubsub + WebSocket | VERIFIED | `checkpoint_eval.py` publishes to `grade:{run_id}`; `websocket.py` grade_stream endpoint subscribes and sends single message |
| 8  | Config editor has Form/Raw toggle; locked params shown greyed with badge | VERIFIED | `ConfigEditor.tsx` useState("form"/"raw"); `ParamForm.tsx` renders "Locked by instructor" badge; 4 tests pass |
| 9  | Student sees anonymous leaderboard ordered by score + WNS tiebreaker | VERIFIED | get_leaderboard() uses `text("(runs.ppa->>'worst_negative_slack')::numeric DESC NULLS LAST")` in ORDER BY when is_postgres=True; idx_runs_wns_numeric functional B-tree index engaged; 3 leaderboard tests pass |
| 10 | User can compare 2-4 runs side-by-side with green/yellow/red highlighting and config diff | VERIFIED | `RunComparison.tsx` METRICS array with higherBetter flags + colorClass(); config diff section shows differing params only |
| 11 | Instructor sees per-student progress with CSV export; student gets 403 | VERIFIED | `courses.py` GET /courses/{id}/dashboard (require_instructor gate) + GET /courses/{id}/dashboard/export (StreamingResponse + csv.writer) |

**Score:** 11/11 truths verified

---

## Gap Closure Verification (Re-verification Focus)

### Closed Gap: Leaderboard WNS DB-Level ORDER BY (DASH-01)

**Previous status:** PARTIAL — Python-side sort only; `idx_runs_wns_numeric` unused

**Fix applied in commits:** `dbcd843` (feat) + `e4ad20d` (test)

**Level 1 — Exists:** `backend/app/api/routes/submissions.py` confirmed present

**Level 2 — Substantive:**
- Line 284: `text("(runs.ppa->>'worst_negative_slack')::numeric DESC NULLS LAST")` present in ORDER BY clause
- Lines 261-265: `is_postgres = "postgresql" in _settings.DATABASE_URL` dialect guard present
- Lines 282-285: text() expression appended to `order_clauses` only when `is_postgres=True`
- Lines 317-328: Python groupby+sort block wrapped in `if not is_postgres:` — only runs on SQLite path

**Level 3 — Wired:**
- `order_clauses` built as list; `.order_by(*order_clauses)` at line 301 uses both clauses on PostgreSQL
- SQLite test path (is_postgres=False): Python-side groupby+sort runs — all existing tests pass
- PostgreSQL production path (is_postgres=True): SQL ORDER BY handles WNS tiebreaker; `sorted_rows = list(rows)` skips Python sort entirely

**Test verification:**
```
tests/test_submissions.py::test_leaderboard_order          PASSED
tests/test_submissions.py::test_leaderboard_anonymity      PASSED
tests/test_submissions.py::test_leaderboard_wns_tiebreaker PASSED

3 passed in 2.92s
```

`test_leaderboard_wns_tiebreaker` (line 544): two students with identical score=80.0, WNS=-0.1 and WNS=-0.3; asserts rank 1 = WNS=-0.1 (less negative = better), rank 2 = WNS=-0.3; docstring names DASH-01 and idx_runs_wns_numeric as the performance contract.

**Closed status: VERIFIED**

---

## Regression Check (Previously Passing Truths)

Quick-pass regression checks on all 10 previously-verified truths:

| Check | Method | Result |
|-------|--------|--------|
| Submissions test suite (8 tests) | `pytest tests/test_submissions.py -q` | 8 passed |
| Backend test suite excluding tile_generator | `pytest tests/ --ignore=test_tile_generator.py -q` | 138 passed |
| text() import in submissions.py | `grep "from sqlalchemy import.*text"` | Present (line 8) |
| get_settings import in submissions.py | `grep "get_settings"` | Present (lines 9, 264) |
| Python groupby+sort still present on SQLite path | Lines 317-325 | Preserved under `if not is_postgres:` guard |

Pre-existing unrelated failure: `tests/test_tile_generator.py::test_generate_png_uploads_to_minio` — `ModuleNotFoundError: No module named 'config'` in worker module path. This failure exists before and after the gap closure; it is not a regression introduced by plan 02-07.

**No regressions detected.**

---

## Required Artifacts

| Artifact | Provides | Status | Details |
|----------|----------|--------|---------|
| `backend/alembic/versions/0003_courses_assignments_submissions.py` | courses, course_enrollments, assignments, submissions tables + B-tree indexes | VERIFIED | down_revision="0002"; all 4 tables created; idx_runs_wns_numeric created via op.execute() |
| `backend/app/models/course.py` | Course ORM with enrollment_code | VERIFIED | Exports Course; enrollment_code unique; relationships to enrollments/assignments |
| `backend/app/models/enrollment.py` | CourseEnrollment ORM | VERIFIED | Exports CourseEnrollment; UniqueConstraint on (course_id, user_id) |
| `backend/app/models/assignment.py` | Assignment ORM with JSONB fields | VERIFIED | Exports Assignment; locked_params, editable_params, checkpoint_rules all JSONB-compatible |
| `backend/app/models/submission.py` | Submission ORM with grading_status | VERIFIED | Exports Submission; checkpoint_results JSONB; grading_status default "pending" |
| `backend/app/models/__init__.py` | All 4 models registered | VERIFIED | Imports Course, CourseEnrollment, Assignment, Submission |
| `backend/app/api/routes/courses.py` | Course CRUD + enrollment + dashboard + CSV | VERIFIED | POST/GET /courses; POST /courses/{id}/enroll; GET /dashboard; GET /dashboard/export with StreamingResponse |
| `backend/app/api/routes/assignments.py` | Assignment CRUD | VERIFIED | POST/GET /courses/{id}/assignments; PATCH /assignments/{id}/open |
| `backend/app/schemas/courses.py` | CourseCreate, CourseResponse, EnrollRequest, EnrollResponse | VERIFIED | Pydantic v2 with from_attributes=True |
| `backend/app/schemas/assignments.py` | AssignmentCreate, AssignmentResponse with locked_params coercion | VERIFIED | field_validator coerces locked_params values to str |
| `backend/app/api/routes/submissions.py` | POST /submit, GET /submissions/mine, GET /preview-score, GET /leaderboard with SQL WNS ORDER BY | VERIFIED | All 4 endpoints present; text() WNS ORDER BY at line 284 guarded by is_postgres; 3 leaderboard tests pass |
| `worker/tasks/checkpoint_eval.py` | evaluate_submission Celery task on background queue | VERIFIED | Pure evaluate_checkpoint_rules() + Celery task; publishes to grade:{run_id} |
| `frontend/src/components/ConfigEditor/ConfigEditor.tsx` | Form/Raw toggle with Monaco | VERIFIED | mode state; Form button + Raw button; ParamForm in form mode; Monaco in raw mode |
| `frontend/src/components/ConfigEditor/ParamForm.tsx` | Form mode with locked param badge | VERIFIED | CURATED_PARAMS rendered; isLocked -> disabled input + "Locked by instructor" span |
| `frontend/src/components/ConfigEditor/ParamMetadata.ts` | CURATED_PARAMS array (7 params) | VERIFIED | All 7 CLAUDE.md params present |
| `backend/app/api/routes/query.py` | GET /query/{run_id} — OpenROAD subprocess | VERIFIED | subprocess.run with docker; linear ODB scan; ownership check; tmpdir cleanup in finally |
| `frontend/src/components/LayoutSnapshot/InspectSidebar.tsx` | Sidebar with dismiss | VERIFIED | Renders null until query made; shows "No element at this location" on empty; dismiss button |
| `frontend/src/components/LayoutSnapshot/LayoutSnapshot.tsx` | Click handler + Y-axis inversion | VERIFIED | handleImageClick with Y-inversion formula; clickToInspect imported and called; InspectSidebar rendered |
| `frontend/src/hooks/useGradeStream.ts` | WebSocket grade hook | VERIFIED | Connects to /ws/runs/{runId}/grade/stream; uses store.setGradeResult; mirrors useLogStream pattern |
| `frontend/src/components/CheckpointCards/CheckpointCards.tsx` | Checkpoint display — preview + result | VERIFIED | Hard gate checkmark/X; scored with points display; preview vs result mode |
| `frontend/src/components/AssignmentView/AssignmentView.tsx` | Instructions/Submit/Leaderboard tabs | VERIFIED | Tab bar with 3 tabs; useGradeStream connected in Submit tab; leaderboard fetch on tab activation |
| `frontend/src/components/RunComparison/RunComparison.tsx` | Side-by-side metrics + config diff | VERIFIED | METRICS array; colorClass() per row; config diff section for differing params only |
| `frontend/src/components/InstructorDashboard/InstructorDashboard.tsx` | Sortable table + CSV export | VERIFIED | Sortable headers; CSV export via anchor href; queue info display |
| `frontend/src/components/CourseNav/CourseNav.tsx` | Sidebar courses section | VERIFIED | Fetches /api/v1/courses on mount; empty state with enrollment code prompt |
| `frontend/src/store/courseSlice.ts` | Zustand slice for courses/grades | VERIFIED | setCourses, setActiveAssignment, setGradeResult actions |
| `frontend/src/api/courses.ts` | getCourses, getLeaderboard, getDashboard, getDashboardExportUrl | VERIFIED | All 4 functions present and typed |
| `frontend/src/api/submissions.ts` | submitRun, getMySubmissions, getPreviewScore | VERIFIED | All 3 functions present |
| `frontend/src/api/query.ts` | clickToInspect with typed InspectElement | VERIFIED | Calls /query/{runId} with x_um, y_um, tolerance_um |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/models/__init__.py` | all 4 new models | `from app.models.course import Course` etc. | WIRED | All 4 imports present in __init__.py |
| migration 0003 | migration chain | `down_revision = "0002"` | WIRED | down_revision = "0002" confirmed |
| `courses.py` | `main.py` | `app.include_router(courses_router, prefix='/api/v1')` | WIRED | main.py registers both courses and assignments routers |
| `enrollment_code` | DB unique constraint | VLSI-YYYY-XXXX format + retry loop | WIRED | generate_enrollment_code() + _generate_unique_code() with 10-attempt retry |
| `submissions.py` | `checkpoint_eval.py` | `evaluate_submission.delay(str(submission.id))` inside handler | WIRED | evaluate_submission.delay() called in handler body |
| `checkpoint_eval.py` | Redis grade channel | `r.publish(f"grade:{run_id}", ...)` | WIRED | r.publish with grade:{run_id} channel confirmed |
| `websocket.py` | `grade:{run_id}` Redis channel | `pubsub.subscribe(f"grade:{run_id}")` | WIRED | subscribe to grade:{run_id} channel confirmed |
| `ConfigEditor.tsx` | `@monaco-editor/react` | `import Editor from '@monaco-editor/react'` | WIRED | Import at line 2 of ConfigEditor.tsx |
| `ParamForm.tsx` | `ParamMetadata.ts` | `import { CURATED_PARAMS } from './ParamMetadata'` | WIRED | ParamMetadata imported and CURATED_PARAMS iterated in render |
| `LayoutSnapshot.tsx` | `GET /api/v1/query/{run_id}` | `clickToInspect(runId, xUm, yUm)` on image click | WIRED | handleImageClick calls clickToInspect; InspectSidebar rendered |
| `query.py` | ORFS container OpenROAD binary | `subprocess.run(['docker', 'run', ..., 'openroad', '-python', '-e', script])` | WIRED | subprocess.run present with docker command |
| `get_leaderboard() ORDER BY` | `idx_runs_wns_numeric` | `text("(runs.ppa->>'worst_negative_slack')::numeric DESC NULLS LAST")` guarded by `is_postgres` | WIRED | Line 284 confirmed; 3 tests pass including test_leaderboard_wns_tiebreaker |
| `GET /courses/{id}/dashboard` | instructor role gate | `_require_instructor()` check | WIRED | _require_instructor(user) called at handler entry |
| `GET /courses/{id}/dashboard/export` | CSV StreamingResponse | `StreamingResponse` + `csv.writer` | WIRED | StreamingResponse + csv.writer + Content-Disposition header confirmed |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| COUR-01 | 02-01, 02-02 | Instructor creates assignment with design, PDK, locked/editable params, checkpoint rules, due date | SATISFIED | `assignments.py` POST endpoint; AssignmentCreate schema with all fields |
| COUR-02 | 02-01, 02-02 | Instructor creates course with VLSI-YYYY-XXXX enrollment code | SATISFIED | generate_enrollment_code() + DB unique constraint retry; regex tested |
| COUR-03 | 02-01, 02-02 | Student enrolls via enrollment code | SATISFIED | POST /courses/{id}/enroll; 404 on bad code; 409 on duplicate |
| COUR-04 | 02-01, 02-04 | Student submits completed run for grading | SATISFIED | POST /assignments/{id}/submit; locked param validation; Celery dispatch |
| COUR-05 | 02-01, 02-04 | System auto-evaluates checkpoints (hard gates + scored + partial credit) | SATISFIED | evaluate_checkpoint_rules() tested: hard gate blocks score, partial credit threshold applied |
| EDIT-01 | 02-01, 02-03 | Config editor guided form mode with locked param enforcement | SATISFIED | ParamForm with locked param greying + "Locked by instructor" badge; ConfigEditor tests pass |
| EDIT-02 | 02-01, 02-03 | Config editor raw Monaco mode | SATISFIED | Editor from @monaco-editor/react in raw mode; mocked in tests; monaco-editor/react in package.json |
| LAYT-02 | 02-01, 02-05 | Click-to-inspect API for layout element details by coordinate | SATISFIED | query.py GET /query/{run_id}; LayoutSnapshot click handler with Y-axis inversion; InspectSidebar |
| DASH-01 | 02-01, 02-06, 02-07 | Anonymous leaderboard with PPA rankings | SATISFIED | text() WNS ORDER BY at DB level (line 284); idx_runs_wns_numeric engaged on PostgreSQL; test_leaderboard_wns_tiebreaker passes |
| DASH-02 | 02-01, 02-06 | Side-by-side run comparison with metrics and config diff | SATISFIED | RunComparison.tsx with color coding; config diff section |
| DASH-03 | 02-01, 02-06 | Instructor class-wide dashboard with per-student progress and queue depth | SATISFIED | GET /courses/{id}/dashboard; CSV export; instructor role gate |

**All 11 Phase 2 requirements covered. No orphaned requirements.**

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None detected in gap closure files | — | — | — | Python-side sort correctly preserved as SQLite fallback; no stubs introduced |

---

## Human Verification Required

### 1. ConfigEditor Form/Raw Toggle in Browser

**Test:** Open a project config tab; click "Raw" button; then click "Form" button
**Expected:** Raw mode shows Monaco editor with makefile syntax highlighting; Form mode shows 7 labeled number inputs with range indicators; no page reload
**Why human:** Monaco editor rendering and syntax highlighting are browser-side; tests mock Monaco; visual confirmation required

### 2. Click-to-Inspect on Real Layout PNG

**Test:** Open a completed run result page; click on a cell in the layout PNG; click on empty whitespace
**Expected:** Clicking a cell shows InspectSidebar with instance name (e.g. u_reg0), master type (e.g. sky130_fd_sc_hd__dfxtp_1), and net names; clicking empty space shows "No element at this location"; sidebar persists until X clicked
**Why human:** Requires live Docker + ORFS image + MinIO with real ODB artifacts; subprocess integration not verifiable in unit tests

### 3. Grade Push End-to-End After Submission

**Test:** Enroll in a course, submit a completed run, observe the grade flow
**Expected:** "Submitted — grading in progress..." banner appears immediately; within 30s CheckpointCards shows per-criterion results (hard gate checkmark/X, scored criteria with points); own row highlighted in leaderboard
**Why human:** Requires running Celery worker, Redis pubsub, live WebSocket connection; end-to-end grading pipeline needs full stack

---

## Summary

**Phase 2 goal is fully achieved** by automated verification criteria. The single gap from the initial verification (DASH-01 leaderboard WNS tiebreaker) was closed by plan 02-07:

- `backend/app/api/routes/submissions.py` now contains `text("(runs.ppa->>'worst_negative_slack')::numeric DESC NULLS LAST")` as the second ORDER BY clause in `get_leaderboard()`, activated via `is_postgres = "postgresql" in settings.DATABASE_URL`
- The functional B-tree index `idx_runs_wns_numeric` (created in migration 0003) is now used by the production PostgreSQL leaderboard query
- The SQLite test path retains the Python-side groupby+sort fallback — all 8 submissions tests pass
- A dedicated `test_leaderboard_wns_tiebreaker` test documents and validates the WNS ordering contract

All 11 observable truths are VERIFIED. All 11 Phase 2 requirements (COUR-01 through COUR-05, EDIT-01, EDIT-02, LAYT-02, DASH-01 through DASH-03) are SATISFIED. No regressions detected across 138 passing backend tests. Three items remain for human verification (Monaco rendering, click-to-inspect with real ODB, and Celery+Redis grade push) — these require the full Docker stack and cannot be verified programmatically.

---

_Verified: 2026-03-15T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes — gap closure after plan 02-07_
