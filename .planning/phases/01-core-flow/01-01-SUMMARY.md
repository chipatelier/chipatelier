---
phase: 01-core-flow
plan: "01"
subsystem: infra
tags: [docker-compose, fastapi, sqlalchemy, alembic, celery, redis, postgresql, pytest, react, typescript, vite]

# Dependency graph
requires: []
provides:
  - Docker Compose stack with postgres, redis, minio, backend, orfs-worker, background-worker, frontend, nginx
  - PostgreSQL schema via Alembic async migration (users, projects, runs, vnc_sessions + GIN/B-tree indexes)
  - FastAPI app skeleton with /healthz endpoint, CORS, lifespan
  - SQLAlchemy 2.0 ORM models (User, Project, Run, VncSession) with JSONBCompatible type
  - Celery queue routing (orfs_jobs + background as two separate worker processes)
  - Wave 0 pytest infrastructure (async_session, test_client, mock_docker, mock_s3, mock_redis)
  - 11 Wave 0 test stub files for all subsequent plans
  - Frontend Vite + React + TypeScript scaffold with strict tsconfig
affects:
  - 01-02 (auth uses Settings, User model, test fixtures)
  - 01-03 (job pipeline uses Run model, Celery tasks, test fixtures)
  - 01-04 (artifacts uses S3 settings, mock_s3 fixture)
  - 01-05 (tile generator uses background queue, tile_generator task stub)
  - 01-06 (VNC uses VncSession model, vnc_session task stub)

# Tech tracking
tech-stack:
  added:
    - fastapi==0.115.*
    - sqlalchemy[asyncio]==2.0.*
    - asyncpg==0.29.*
    - alembic==1.13.*
    - pydantic-settings==2.*
    - PyJWT==2.10.*
    - argon2-cffi==25.*
    - celery[redis]==5.4.*
    - redis[asyncio]==5.*
    - boto3==1.35.*
    - docker==7.1.*
    - pytest==8.* + pytest-asyncio==0.24.*
    - moto[s3] (S3 mocking)
    - fakeredis (Redis mocking)
    - aiosqlite (in-memory SQLite for tests)
    - react@18.3 + typescript@5.6 + vite@5.4
    - zustand@5 + axios@1.7 + @xterm/xterm@5.5
  patterns:
    - SQLAlchemy 2.0 DeclarativeBase with Mapped[] type annotations
    - pydantic-settings Settings class with lru_cache for dependency injection
    - Async DB session via get_db() generator (FastAPI dependency)
    - JSONBCompatible TypeDecorator: JSONB on PostgreSQL, JSON on SQLite for test isolation
    - Alembic async migration pattern: asyncio.run + AsyncConnection.run_sync
    - Celery with worker_prefetch_multiplier=1 and task_acks_late=True for long ORFS jobs
    - Two dedicated Celery worker processes (never merged into one)

key-files:
  created:
    - docker-compose.yml
    - .env.example
    - backend/pyproject.toml
    - backend/app/main.py
    - backend/app/core/config.py
    - backend/app/core/database.py
    - backend/app/core/redis.py
    - backend/app/models/base.py
    - backend/app/models/types.py
    - backend/app/models/user.py
    - backend/app/models/project.py
    - backend/app/models/run.py
    - backend/app/models/vnc_session.py
    - backend/alembic.ini
    - backend/alembic/env.py
    - backend/alembic/versions/0001_initial_schema.py
    - backend/pytest.ini
    - backend/tests/conftest.py
    - worker/celery_app.py
    - worker/celeryconfig.py
    - worker/tasks/orfs_job.py
    - worker/tasks/tile_generator.py
    - worker/tasks/vnc_session.py
    - frontend/package.json
    - frontend/tsconfig.json
    - frontend/vite.config.ts
    - frontend/src/App.tsx
    - frontend/src/main.tsx
    - infra/nginx/nginx.conf
  modified: []

key-decisions:
  - "JSONBCompatible TypeDecorator uses JSONB on PostgreSQL and falls back to JSON on SQLite — allows test isolation without separate test models"
  - "ppa and config are separate JSONB columns on runs table — ppa holds metrics only (WNS/TNS/DRC), config holds config.mk snapshot"
  - "Two dedicated Celery worker processes (orfs-worker for orfs_jobs, background-worker for tiles/VNC/grading) — architectural lock, never merge"
  - "pytest uses SQLite in-memory engine (aiosqlite) for test speed; integration tests marked separately"

patterns-established:
  - "Pattern: async DB session via get_db() generator injected as FastAPI dependency"
  - "Pattern: JSONBCompatible for dialect-agnostic JSONB columns"
  - "Pattern: Wave 0 test stubs — all 11 test files exist as importable stubs from day 1"
  - "Pattern: Alembic async migration via asyncio.run(run_async_migrations())"

requirements-completed: [JOB-01, JOB-02]

# Metrics
duration: 8min
completed: 2026-03-13
---

# Phase 1 Plan 01: Stack Bootstrap and Wave 0 Infrastructure Summary

**Docker Compose full-stack with PostgreSQL/Alembic schema, async FastAPI skeleton, dual Celery queue routing, and Wave 0 pytest fixtures backing 71 tests**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-13T07:38:00Z
- **Completed:** 2026-03-13T07:46:24Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 59 files created

## Accomplishments

- Docker Compose stack with 8 services (postgres, redis, minio, backend, orfs-worker, background-worker, frontend, nginx), all with health checks and correct queue routing
- Alembic async migration 0001 creates users, projects, runs, vnc_sessions tables with GIN indexes on ppa/config JSONB and functional B-tree indexes on worst_negative_slack/CLOCK_PERIOD
- FastAPI app with /healthz endpoint, CORS middleware, lifespan (init_db on startup)
- Celery queue routing: orfs_job.* -> orfs_jobs queue; tile_generator.*/vnc_session.* -> background queue; worker_prefetch_multiplier=1 prevents ORFS task hoarding
- Wave 0 pytest infrastructure: conftest.py with 5 fixtures (async_session, test_client, mock_docker, mock_s3/moto, mock_redis/fakeredis) + 11 Wave 0 stub test files (71 tests passing)
- Frontend scaffold: Vite 5 + React 18 + TypeScript strict mode, zustand, xterm.js, axios

## Task Commits

1. **Task 1: Docker Compose stack, backend skeleton, SQLAlchemy models** - `a9d3a2d` (feat)
2. **Task 2: Alembic migrations, Celery config, Wave 0 pytest, frontend scaffold** - `d482c22` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `docker-compose.yml` - 8-service stack with health checks, named volumes, dual Celery workers
- `.env.example` - All required env vars with defaults
- `backend/app/core/config.py` - pydantic-settings Settings with lru_cache
- `backend/app/core/database.py` - Async SQLAlchemy engine + get_db() generator
- `backend/app/core/redis.py` - Async Redis connection pool (lazy init)
- `backend/app/models/types.py` - JSONBCompatible TypeDecorator (JSONB/JSON dialect switch)
- `backend/app/models/{user,project,run,vnc_session}.py` - SQLAlchemy 2.0 ORM models
- `backend/app/main.py` - FastAPI app, CORS, lifespan, /healthz, router stubs
- `backend/alembic/versions/0001_initial_schema.py` - Full schema + GIN/B-tree indexes
- `backend/alembic/env.py` - Async migration pattern (asyncio.run + run_sync)
- `backend/tests/conftest.py` - Wave 0 fixtures (5 fixtures)
- `backend/tests/test_*.py` - 11 Wave 0 stub files
- `worker/celery_app.py + celeryconfig.py` - Celery with dual-queue routing
- `worker/tasks/{orfs_job,tile_generator,vnc_session}.py` - Task stubs
- `frontend/` - Vite + React + TypeScript scaffold
- `infra/nginx/nginx.conf` - Reverse proxy with WebSocket upgrade

## Decisions Made

- JSONBCompatible TypeDecorator for JSONB/SQLite compatibility in tests — avoids separate test model definitions
- ppa and config are separate JSONB columns (plan spec: ppa = metrics only, config = config.mk snapshot)
- Two dedicated Celery worker processes — architectural lock from CLAUDE.md, never merge
- pytest uses SQLite in-memory (aiosqlite) for test speed; integration tests marked with `@pytest.mark.integration`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed PostgreSQL JSONB type incompatibility with SQLite in-memory tests**
- **Found during:** Task 1 (running tests after writing Run model)
- **Issue:** `sqlalchemy.dialects.postgresql.JSONB` raises `UnsupportedCompilationError` when SQLite (aiosqlite) tries to create the schema during test setup
- **Fix:** Created `backend/app/models/types.py` with `JSONBCompatible` TypeDecorator that renders `JSONB` on PostgreSQL and falls back to `JSON` on all other dialects (including SQLite)
- **Files modified:** `backend/app/models/types.py` (created), `backend/app/models/run.py` (updated ppa/config/stage_metrics columns)
- **Verification:** 13/13 Task 1 tests pass after fix; JSONB GIN index in migration file is unaffected (migration runs against PostgreSQL only)
- **Committed in:** a9d3a2d (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Essential for test infrastructure correctness. JSONBCompatible is additive — PostgreSQL production behavior unchanged, tests now run reliably.

## Issues Encountered

None beyond the JSONB/SQLite incompatibility resolved above.

## User Setup Required

None — no external service configuration required. Copy `.env.example` to `.env` before running `docker compose up`.

## Next Phase Readiness

- All Wave 0 test fixtures ready for plans 01-02 through 01-06
- Database schema defined; Alembic migration ready for `alembic upgrade head` once PostgreSQL is running
- docker compose stack validated (`docker compose config` passes)
- Plan 01-02 (auth + projects API) can start immediately

---

## Self-Check: PASSED

All required files exist. Commits a9d3a2d and d482c22 verified in git log.

---
*Phase: 01-core-flow*
*Completed: 2026-03-13*
