---
phase: 02-learning-layer
plan: "07"
subsystem: api
tags: [fastapi, sqlalchemy, postgresql, sqlite, leaderboard, jsonb, btree-index]

# Dependency graph
requires:
  - phase: 02-learning-layer
    provides: "Leaderboard endpoint, idx_runs_wns_numeric B-tree index (02-06), migration 0003 (02-01)"
provides:
  - "SQL-level WNS ORDER BY in get_leaderboard() using text() expression with ::numeric cast"
  - "idx_runs_wns_numeric functional B-tree index now used by production PostgreSQL leaderboard query"
  - "test_leaderboard_wns_tiebreaker test validating WNS tiebreaker ordering contract"
  - "Dialect guard: PostgreSQL uses DB-level ORDER BY; SQLite uses Python-side fallback"
affects: [leaderboard, grading, submissions, testing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dialect-conditional ORDER BY: check settings.DATABASE_URL for 'postgresql', not session.bind introspection"
    - "SQLAlchemy text() for raw SQL expressions in order_by() — used when ORM column expressions cannot express JSONB ::numeric cast"
    - "Python-side sort as fallback only when is_postgres=False; PostgreSQL path skips Python sort entirely"

key-files:
  created: []
  modified:
    - backend/app/api/routes/submissions.py
    - backend/tests/test_submissions.py

key-decisions:
  - "Dialect detection uses settings.DATABASE_URL.startswith check (not db.bind.dialect.name) — async session bind may be None, settings is always available"
  - "Python groupby+sort preserved on SQLite path — keeps all existing tests passing without schema changes"
  - "test_leaderboard_wns_tiebreaker is a dedicated named test documenting DASH-01 and idx_runs_wns_numeric as the performance contract"

patterns-established:
  - "Conditional order_clauses list pattern: build list first, extend conditionally, then .order_by(*order_clauses)"

requirements-completed: [DASH-01]

# Metrics
duration: 2min
completed: 2026-03-15
---

# Phase 2 Plan 07: Leaderboard WNS DB-Level ORDER BY Summary

**SQL-level WNS tiebreaker added to get_leaderboard() with PostgreSQL/SQLite dialect guard — closes DASH-01 gap by routing production queries through idx_runs_wns_numeric B-tree index**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-15T22:13:17Z
- **Completed:** 2026-03-15T22:15:13Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `text("(runs.ppa->>'worst_negative_slack')::numeric DESC NULLS LAST")` as second ORDER BY clause in `get_leaderboard()`, activated only when `is_postgres=True`
- Dialect detection via `"postgresql" in settings.DATABASE_URL` — avoids unreliable async session bind inspection
- Python-side `groupby+sort` fallback preserved under `if not is_postgres:` — all existing SQLite tests continue to pass
- Added `test_leaderboard_wns_tiebreaker` test: two students with identical score=80.0, WNS=-0.1 and WNS=-0.3; asserts rank 1 goes to WNS=-0.1 (less negative = better)

## Task Commits

1. **Task 1: Add SQL-level WNS ORDER BY with dialect guard** - `dbcd843` (feat)
2. **Task 2: Add test_leaderboard_wns_tiebreaker** - `e4ad20d` (test)

## Files Created/Modified

- `backend/app/api/routes/submissions.py` - Added `get_settings()` import, `is_postgres` dialect check, conditional `order_clauses` list with `text()` WNS expression, `if not is_postgres:` guard around Python sort
- `backend/tests/test_submissions.py` - Added `test_leaderboard_wns_tiebreaker` test with full setup and 5 assertions including explicit `float(entries[0]["wns"]) > float(entries[1]["wns"])` ordering check

## Decisions Made

- Dialect detection uses `settings.DATABASE_URL` (not `db.bind.dialect.name`) — async sessions may have `bind=None`; settings is always available via the `lru_cache`-backed `get_settings()` singleton
- Python-side sort preserved as fallback (not removed) — keeps SQLite tests working without any test infrastructure changes

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- DASH-01 gap is fully closed: `idx_runs_wns_numeric` functional B-tree index is now used by the production PostgreSQL leaderboard query
- All 3 leaderboard tests pass: `test_leaderboard_order`, `test_leaderboard_anonymity`, `test_leaderboard_wns_tiebreaker`
- Phase 2 gap closure complete — no remaining open gaps flagged in STATE.md

---
*Phase: 02-learning-layer*
*Completed: 2026-03-15*
