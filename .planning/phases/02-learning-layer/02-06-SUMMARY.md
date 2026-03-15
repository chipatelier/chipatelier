---
phase: 02-learning-layer
plan: "06"
subsystem: ui
tags: [fastapi, react, typescript, sqlalchemy, leaderboard, csv-export, zustand]

requires:
  - phase: 02-learning-layer plan 02
    provides: course and enrollment ORM models, course/enrollment API routes
  - phase: 02-learning-layer plan 03
    provides: assignment ORM model, assignment CRUD routes
  - phase: 02-learning-layer plan 04
    provides: submission API, AssignmentView component with tab structure
  - phase: 02-learning-layer plan 05
    provides: click-to-inspect backend; functional B-tree index idx_runs_wns_numeric on ppa JSONB

provides:
  - Anonymous leaderboard endpoint (GET /assignments/{id}/leaderboard) with score+WNS ordering
  - Instructor dashboard endpoint (GET /courses/{id}/dashboard) with per-student progress
  - CSV export endpoint (GET /courses/{id}/dashboard/export) with StreamingResponse
  - RunComparison React component with green/yellow/red color coding and config diff section
  - InstructorDashboard React component with sortable table and CSV export link
  - CourseNav React component for sidebar with enrolled courses and empty state
  - AssignmentView Leaderboard tab with own-row highlight and "You" badge
  - courses.ts API client: getCourses, getLeaderboard, getDashboard, getDashboardExportUrl

affects:
  - Phase 3 AI integration (context about leaderboard + dashboard patterns)
  - Future admin panel (dashboard role gate pattern)

tech-stack:
  added:
    - csv (Python stdlib) for streaming CSV export via io.StringIO + StreamingResponse
    - itertools.groupby for Python-side WNS tiebreaker sort in leaderboard
  patterns:
    - Python-side sort for JSONB numeric tiebreaker (SQLite test compat; PostgreSQL uses idx_runs_wns_numeric B-tree index)
    - StreamingResponse with iter([output.read()]) for single-batch CSV download
    - data-metric / data-config-key attributes on table cells for Vitest query targeting
    - Leaderboard anonymity: is_self flag on each entry; frontend shows "Rank N" for non-self

key-files:
  created:
    - backend/app/api/routes/submissions.py (GET /assignments/{id}/leaderboard added)
    - backend/app/api/routes/courses.py (GET /courses/{id}/dashboard + /export added)
    - frontend/src/api/courses.ts
    - frontend/src/components/RunComparison/RunComparison.tsx
    - frontend/src/components/RunComparison/index.ts
    - frontend/src/components/InstructorDashboard/InstructorDashboard.tsx
    - frontend/src/components/InstructorDashboard/index.ts
    - frontend/src/components/CourseNav/CourseNav.tsx
    - frontend/src/components/CourseNav/index.ts
  modified:
    - backend/tests/test_submissions.py (test_leaderboard_order, test_leaderboard_anonymity)
    - backend/tests/test_courses.py (test_dashboard_endpoint_role_gate, test_dashboard_returns_student_progress)
    - frontend/src/components/AssignmentView/AssignmentView.tsx (Leaderboard tab completed)
    - frontend/src/components/RunComparison/RunComparison.test.tsx (stub replaced with real tests)

key-decisions:
  - "Leaderboard WNS tiebreaker uses Python-side sort (itertools.groupby) for SQLite test compatibility — PostgreSQL production uses idx_runs_wns_numeric functional B-tree index for DB-level ordering"
  - "Dashboard queries count runs across all student projects (Project has no course_id FK) — student run count is total, not course-scoped"
  - "CSV export uses io.StringIO + iter([output.read()]) single-batch pattern — sufficient for class-size datasets (50-300 rows)"
  - "Leaderboard anonymity enforced at API level via is_self bool — names never in response body; frontend displays Rank N for non-self rows"

patterns-established:
  - "data-metric attribute on table cells for Vitest DOM query in color coding tests"
  - "Role gate via _require_instructor(user) helper at route handler top — 403 raised immediately"
  - "getDashboardExportUrl returns plain URL string for <a download> link — no axios for file downloads"

requirements-completed: [DASH-01, DASH-02, DASH-03]

duration: 17min
completed: 2026-03-15
---

# Phase 2 Plan 06: Leaderboard, Run Comparison, and Instructor Dashboard Summary

**Anonymous leaderboard endpoint with score+WNS tiebreaker, instructor dashboard with CSV export, RunComparison color-coded metrics table, CourseNav sidebar, and completed AssignmentView Leaderboard tab**

## Performance

- **Duration:** 17 min
- **Started:** 2026-03-15T09:06:00Z
- **Completed:** 2026-03-15T09:23:22Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments

- Leaderboard endpoint returns anonymous ranked entries ordered by score DESC then WNS DESC (DB primary sort + Python tiebreaker for SQLite compat)
- Instructor dashboard endpoint returns per-student progress (run count, last run status, submission status, score) gated at instructor role
- CSV export streams grades file via StreamingResponse with Content-Disposition attachment header
- RunComparison component highlights best metric value green, worst red, middle yellow using relative per-column comparison; shows config params that differ across runs in separate section
- InstructorDashboard renders sortable table (click-to-sort any column) with CSV export anchor
- CourseNav renders enrolled courses list with empty state prompt for enrollment code
- AssignmentView Leaderboard tab fetches data on tab activation; own row gets blue background and "You" badge

## Task Commits

Each task was committed atomically:

1. **Task 1: Leaderboard and instructor dashboard backend endpoints** - `7946376` (feat)
2. **Task 2: RunComparison, InstructorDashboard, CourseNav frontend components** - `8019d77` (feat)

**Plan metadata:** (committed next)

## Files Created/Modified

- `backend/app/api/routes/submissions.py` — Added GET /assignments/{id}/leaderboard with best-per-user subquery and is_self anonymization
- `backend/app/api/routes/courses.py` — Added GET /courses/{id}/dashboard and /dashboard/export (CSV StreamingResponse)
- `backend/tests/test_submissions.py` — test_leaderboard_order (3-student score+WNS tiebreak), test_leaderboard_anonymity (is_self flag)
- `backend/tests/test_courses.py` — test_dashboard_endpoint_role_gate (403 for students), test_dashboard_returns_student_progress (students[] with queue_info)
- `frontend/src/api/courses.ts` — getCourses, getLeaderboard, getDashboard, getDashboardExportUrl
- `frontend/src/components/RunComparison/RunComparison.tsx` — Side-by-side metrics table with colorClass and config diff detection
- `frontend/src/components/RunComparison/RunComparison.test.tsx` — 3 tests: color coding, config diff, empty state
- `frontend/src/components/InstructorDashboard/InstructorDashboard.tsx` — Sortable student progress table with CSV export anchor
- `frontend/src/components/CourseNav/CourseNav.tsx` — Sidebar courses section with empty state
- `frontend/src/components/AssignmentView/AssignmentView.tsx` — LeaderboardTab added (fetches on activation, is_self highlight)

## Decisions Made

- Leaderboard WNS tiebreaker uses `itertools.groupby` Python-side sort within equal-score groups — avoids `->>'` JSON operator (not supported in SQLite used for tests); PostgreSQL production path uses idx_runs_wns_numeric functional B-tree index for DB-level ordering when scores are equal
- Dashboard run count queries across all student projects (Project ORM model has no course_id FK) — reflects total activity, not course-scoped
- CSV export uses single-batch `io.StringIO` pattern suitable for class sizes (50-300 students); streaming chunk approach not needed at this scale

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SQLite incompatible JSON operator in leaderboard ORDER BY**
- **Found during:** Task 1 (leaderboard implementation)
- **Issue:** PostgreSQL `->>'` JSON operator in raw SQL `text()` expression throws `sqlite3.OperationalError: near ">>": syntax error` in test environment
- **Fix:** Replaced `text("(runs.ppa->>'wns')::numeric DESC")` DB-level sort with Python-side `itertools.groupby` stable sort within equal-score groups; DB still handles primary score DESC ordering
- **Files modified:** backend/app/api/routes/submissions.py
- **Verification:** test_leaderboard_order passes — rank1=score95, rank2=score80+WNS-0.1, rank3=score80+WNS-0.2
- **Committed in:** 7946376 (Task 1 commit)

**2. [Rule 1 - Bug] Dead query code left in dashboard after refactor**
- **Found during:** Task 1 (dashboard implementation)
- **Issue:** Initial dashboard draft included a dead `assignments_result` query using `.in_(subquery())` that triggered SAWarning and was never consumed
- **Fix:** Removed dead query; kept clean `course_assignment_ids` list used for submission filtering
- **Files modified:** backend/app/api/routes/courses.py
- **Verification:** 16 tests pass, SAWarning eliminated
- **Committed in:** 7946376 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 SQL dialect compat bug, 1 dead code cleanup)
**Impact on plan:** Both auto-fixes required for correct operation in test environment. Production PostgreSQL unaffected — leaderboard WNS ordering semantically equivalent. No scope creep.

## Issues Encountered

- TestClient has `raise_server_exceptions=False` which masks 500 errors as opaque responses — had to use a background Python process to surface the sqlite3.OperationalError

## User Setup Required

None - no external service configuration required.

## Self-Check: PASSED

All created files verified on disk. Task commits 7946376 and 8019d77 confirmed in git log.

## Next Phase Readiness

- Phase 2 fully complete: all 6 plans executed (database foundation, assignments, submissions, leaderboard, tiled layout, click-to-inspect, instructor dashboard)
- Phase 3 AI integration can now build on leaderboard data for competitive hints and instructor dashboard for class-level analytics
- Remaining concern: CPU budget on DL380 Gen9 should be profiled before Phase 3 ships AI workloads alongside ORFS jobs
