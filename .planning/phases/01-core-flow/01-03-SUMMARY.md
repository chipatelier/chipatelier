---
phase: 01-core-flow
plan: "03"
subsystem: api
tags: [fastapi, celery, docker, boto3, minio, redis, sqlalchemy, pydantic]

# Dependency graph
requires:
  - phase: 01-core-flow plan 01-01
    provides: Run, Project, User ORM models; Alembic schema; Celery app skeleton
  - phase: 01-core-flow plan 01-02
    provides: get_current_user dependency; JWT auth; get_db dependency

provides:
  - POST/GET /api/v1/projects — project CRUD with ownership checks
  - POST /api/v1/projects/{id}/upload — multi-file MinIO upload (.v/.sv/.mk)
  - GET /api/v1/projects/{id}/runs — run list with PPA metrics
  - POST /api/v1/jobs/submit — single-active-run constraint, Celery dispatch, 409 conflict
  - GET /api/v1/jobs/{id} — run status and stage_completed
  - DELETE /api/v1/jobs/{id} — cancel with Celery SIGTERM revoke
  - StorageService — boto3 S3v4 MinIO wrapper (upload, presigned URL, delete_prefix)
  - ContainerManager — Docker SDK wrapper with all security constraints
  - run_orfs_job Celery task — full container lifecycle with always-cleanup finally
  - cleanup_orphaned_containers beat task — 120s watchdog
  - Stage separator lines injected into Redis log stream at ORFS stage transitions

affects:
  - 01-04 (log streaming — depends on Redis pubsub logs:{run_id} and logbuf:{run_id})
  - 01-05 (artifacts/results — depends on run status transitions and artifact_path)
  - 01-06 (Docker Compose — needs worker container config with celery beat)

# Tech tracking
tech-stack:
  added:
    - boto3 (S3/MinIO client, S3v4 signature required)
    - docker (Docker SDK for Python)
    - sqlalchemy sync engine (for Celery task DB access — asyncpg not usable in sync context)
  patterns:
    - FastAPI dependency injection for StorageService (app.dependency_overrides in tests)
    - Celery task imports app settings inside function body (avoids circular imports)
    - SQLAlchemy sync engine via URL replace postgresql+asyncpg → postgresql for Celery tasks
    - always-cleanup finally block: container stop+remove + workspace rmtree
    - worker sys.path: project root added in conftest.py for worker/ importability in tests

key-files:
  created:
    - backend/app/services/storage_service.py
    - backend/app/schemas/projects.py
    - backend/app/schemas/jobs.py
    - backend/app/api/routes/projects.py
    - backend/app/api/routes/jobs.py
    - worker/container/__init__.py
    - worker/container/manager.py
    - worker/tasks/watchdog.py
  modified:
    - backend/app/models/run.py (added celery_task_id VARCHAR nullable)
    - backend/app/main.py (registered projects_router and jobs_router)
    - worker/tasks/orfs_job.py (full implementation replacing stub)
    - worker/celeryconfig.py (added beat_schedule and watchdog routing)
    - backend/tests/conftest.py (sys.path for worker/ importability)
    - backend/tests/test_projects.py (full test suite)
    - backend/tests/test_jobs.py (full test suite)
    - backend/tests/test_container.py (full test suite)

key-decisions:
  - "Patch worker.tasks.orfs_job.run_orfs_job not app.api.routes.jobs.run_orfs_job — function is imported inside submit handler to avoid circular imports, so module-level patch target is the source module"
  - "Use app.dependency_overrides for StorageService in tests, not unittest.mock.patch — FastAPI stores dependency function reference at registration time, patching the module attribute after does not affect the stored reference"
  - "sys.path injection in conftest.py adds project root so worker/ is importable from backend/tests/ — avoids duplicating test code into worker/tests/"
  - "Celery task uses synchronous SQLAlchemy create_engine (postgresql://) with URL replace — asyncpg driver cannot run in synchronous Celery task context"
  - "storage-opt size= commented out in ContainerManager — overlay2 + pquota mount option not guaranteed on all RHEL/Rocky 9 deployments; documented as opt-in"

patterns-established:
  - "Pattern: FastAPI dependency overrides for external services (storage, celery) in tests"
  - "Pattern: Local import of Celery tasks inside route handlers to avoid circular imports between backend/ and worker/"
  - "Pattern: Synchronous SQLAlchemy engine in Celery tasks via DATABASE_URL replace (asyncpg → psycopg2)"
  - "Pattern: always-cleanup in Celery tasks: try/except/finally with container.stop_and_remove() + shutil.rmtree()"

requirements-completed: [JOB-01, JOB-02, JOB-04, JOB-05]

# Metrics
duration: 15min
completed: 2026-03-13
---

# Phase 01 Plan 03: Job Pipeline Summary

**Project CRUD + multi-file MinIO upload, ORFS container lifecycle with network isolation and always-cleanup finally, job submit/status/cancel endpoints with 409 single-run constraint, and 120s orphaned-container watchdog via Celery beat**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-13T08:00:46Z
- **Completed:** 2026-03-13T08:15:41Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments

- Working job submission pipeline: browser submits Verilog → MinIO upload → DB run record → Celery dispatch → ORFS container → log stream → cleanup
- ORFS container enforces all security constraints: network=none, cgroup CPU/RAM limits, read_only filesystem, tmpfs /tmp, cap_drop ALL, no-new-privileges, user=orfs:orfs
- Stage transition detection injects visual separator lines into Redis log stream at synthesis/floorplan/place/cts/route/gds boundaries
- Single-active-run constraint enforced with 409 response before job can be double-submitted
- Orphaned container watchdog scheduled every 120s via Celery beat as defense against worker crash

## Task Commits

1. **Task 1: Storage service, project endpoints, job submit/status/cancel API** - `3bdfeb4` (feat)
2. **Task 2: ORFS container manager, orfs_job Celery task, orphaned-container watchdog** - `ab4260e` (feat)

## Files Created/Modified

- `backend/app/services/storage_service.py` — boto3 S3v4 MinIO wrapper with upload, presigned URL, delete_prefix
- `backend/app/schemas/projects.py` — ProjectCreate/Response, RunSummary, UploadResponse schemas
- `backend/app/schemas/jobs.py` — SubmitRequest/Response, RunStatusResponse schemas
- `backend/app/api/routes/projects.py` — POST/GET/upload/runs project endpoints
- `backend/app/api/routes/jobs.py` — submit/status/cancel job endpoints with single-run constraint
- `backend/app/models/run.py` — added celery_task_id field for cancel support
- `backend/app/main.py` — registered projects_router and jobs_router
- `worker/container/manager.py` — Docker SDK wrapper: run_container, stop_and_remove, list_orfs_containers
- `worker/tasks/orfs_job.py` — full Celery task: container lifecycle, log streaming, stage detection
- `worker/tasks/watchdog.py` — cleanup_orphaned_containers beat task
- `worker/celeryconfig.py` — beat_schedule with 120s watchdog + route mapping
- `backend/tests/conftest.py` — sys.path for worker/ importability
- `backend/tests/test_projects.py` — 11 tests covering project CRUD and upload
- `backend/tests/test_jobs.py` — 9 tests covering submit/status/cancel/409
- `backend/tests/test_container.py` — 9 tests covering JOB-02 security constraints

## Decisions Made

- FastAPI `Depends(get_storage_service)` stores the function reference at import time, so `patch("app.api.routes.projects.get_storage_service")` doesn't work — must use `app.dependency_overrides[get_storage_service] = lambda: mock_svc` in tests
- `run_orfs_job` is imported inside `submit_job()` handler body (not at module top) to break the circular import chain between `backend/` and `worker/`; tests patch at `worker.tasks.orfs_job.run_orfs_job`
- `storage_opt size=` commented out: requires overlay2 + pquota on RHEL/Rocky 9 — too fragile to enable by default; disk quotas at OS level instead
- sys.path injection in conftest adds project root so `worker` is importable from backend test suite without duplicating test infrastructure

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] App dependency override pattern for StorageService in tests**
- **Found during:** Task 1 (upload test failure — 500 Internal Server Error)
- **Issue:** Plan specified `patch("app.api.routes.projects.get_storage_service")` but FastAPI captures the dependency function reference at route registration time, making module-level patching ineffective
- **Fix:** Used `app.dependency_overrides[get_storage_service] = lambda: mock_svc` in test; this is the correct FastAPI testing pattern
- **Files modified:** `backend/tests/test_projects.py`
- **Verification:** Upload tests pass

**2. [Rule 3 - Blocking] Added project root to sys.path in conftest for worker importability**
- **Found during:** Task 1 (job submit test — ModuleNotFoundError: No module named 'worker')
- **Issue:** Backend tests run from `backend/` dir but need to import `worker.tasks.orfs_job` for patching; worker/ is at project root, not on Python path
- **Fix:** Added `sys.path.insert(0, project_root)` in `conftest.py` where project_root = `../../`
- **Files modified:** `backend/tests/conftest.py`
- **Verification:** All job and container tests pass

---

**Total deviations:** 2 auto-fixed (1 missing critical pattern, 1 blocking import)
**Impact on plan:** Both auto-fixes necessary for testability. No scope creep.

## Issues Encountered

None beyond the deviations documented above.

## Next Phase Readiness

- Job pipeline is complete; plans 01-04 (log streaming) and 01-05 (artifacts) can now be built on top
- Redis pubsub channels `logs:{run_id}` and `logbuf:{run_id}` are ready for WebSocket consumer
- `generate_png.delay()` call in `run_orfs_job` is a no-op stub until plan 01-05 implements `tile_generator.generate_png`
- Container security constraints verified by test suite; production deployment should verify overlay2 + pquota for disk quotas

---
*Phase: 01-core-flow*
*Completed: 2026-03-13*

## Self-Check: PASSED

All files exist. All commits verified:
- 3bdfeb4: Task 1 (project/job API)
- ab4260e: Task 2 (container manager, orfs_job, watchdog)
