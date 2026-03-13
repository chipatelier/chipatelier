---
phase: 01-core-flow
plan: "05"
subsystem: api
tags: [ppa-metrics, klayout, minio, presigned-urls, react, typescript, celery]

requires:
  - phase: 01-core-flow plan 01-02
    provides: User/Project/Run ORM models, auth system
  - phase: 01-core-flow plan 01-03
    provides: StorageService (upload_file, generate_download_url), ORFS job runner, workspace layout
provides:
  - parse_ppa_metrics() reading ORFS METRICS2.1 metadata.json (WNS/TNS/DRC/area/power)
  - generate_png Celery task: KLayout headless PNG upload to MinIO (permanent fast-path)
  - GET /api/v1/jobs/{id}/artifacts returning presigned URLs for GDS/DEF/PNG/timing (1hr)
  - PpaMetricCards component: 5-card grid with green/yellow/red color thresholds
  - LayoutSnapshot component: PNG + VNC button (locked position) + download links
  - RunHistoryTable component: clickable run list with status badges and PPA columns
  - Results tab wired in RunDetailPage: auto-activates on job completion
affects:
  - 01-06 (VNC session — LayoutSnapshot has VNC button stub ready for wiring)
  - Phase 2 tiled viewer (tile_generator.py has PNG fast-path documented as permanent)

tech-stack:
  added: []
  patterns:
    - parse_ppa_metrics uses ORFS METRICS2.1 key names (timing__setup__ws, route__drc_errors__count)
    - _try_presign() wraps generate_download_url; returns None on ClientError for missing artifacts
    - generate_png dispatched on background Celery queue; uses synchronous SQLAlchemy engine for DB update
    - TDD: tests written before implementation; patched at app.core.config.get_settings (not module-level)

key-files:
  created:
    - backend/app/services/metrics_service.py
    - backend/app/schemas/artifacts.py
    - backend/app/api/routes/artifacts.py
    - frontend/src/api/artifacts.ts
    - frontend/src/components/PpaMetricCards/PpaMetricCards.tsx
    - frontend/src/components/PpaMetricCards/index.ts
    - frontend/src/components/LayoutSnapshot/LayoutSnapshot.tsx
    - frontend/src/components/LayoutSnapshot/index.ts
    - frontend/src/components/RunHistoryTable/RunHistoryTable.tsx
    - frontend/src/components/RunHistoryTable/index.ts
  modified:
    - worker/tasks/tile_generator.py
    - backend/app/main.py
    - backend/tests/test_metrics.py
    - backend/tests/test_artifacts.py
    - backend/tests/test_tile_generator.py
    - frontend/src/api/jobs.ts
    - frontend/src/pages/RunDetailPage.tsx
    - frontend/src/pages/ProjectPage.tsx

key-decisions:
  - "ORFS METRICS2.1 key names used in parse_ppa_metrics: timing__setup__ws, timing__setup__tns, route__drc_errors__count, design__instance__area, power__total, flow__platform__status — must verify against actual ORFS run output during integration testing"
  - "generate_png is permanent fast-path — tile_generator.py module docstring and function docstring both document this constraint; Phase 2 tiled viewer must not remove PNG path"
  - "Artifacts endpoint uses _try_presign() helper that returns None on ClientError rather than raising — allows partial responses when some artifacts are missing"
  - "RunStatusResponse type extended with config field to expose config JSONB in frontend"

patterns-established:
  - "Patch at app.core.config.get_settings (not worker.tasks.tile_generator.get_settings) since get_settings is called inside function body via lazy import"
  - "Background task DB updates use synchronous SQLAlchemy engine (postgresql:// not postgresql+asyncpg://) since Celery tasks run in sync context"

requirements-completed:
  - RSLT-01
  - RSLT-02
  - RSLT-03
  - RSLT-04

duration: 9min
completed: 2026-03-13
---

# Phase 01 Plan 05: Artifact Collection and Results Display Summary

**PPA metrics parsed from ORFS METRICS2.1 metadata.json, KLayout headless PNG generation to MinIO, presigned download URLs API, and Results tab UI with color-coded metric cards and layout snapshot**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-13T08:30:26Z
- **Completed:** 2026-03-13T08:40:19Z
- **Tasks:** 2
- **Files modified:** 18 (10 created, 8 modified)

## Accomplishments
- Implemented `parse_ppa_metrics()` reading ORFS METRICS2.1 metadata.json; gracefully returns defaults on missing/malformed file
- Implemented `generate_png` Celery background task: KLayout headless PNG render, MinIO upload, run record update with PPA and artifact_path; handles missing klayout gracefully
- Added `GET /api/v1/jobs/{id}/artifacts` returning presigned URLs (1hr) for GDS, DEF, timing report, and layout PNG
- Built PpaMetricCards (5 cards, green/yellow/red thresholds), LayoutSnapshot (PNG + VNC stub + download links), and RunHistoryTable (clickable rows with status badges and PPA columns)
- Wired Results tab in RunDetailPage: auto-switches on job completion, fetches artifacts, renders PpaMetricCards + LayoutSnapshot

## Task Commits

Each task was committed atomically:

1. **Task 1: PPA metrics parsing, KLayout PNG generation task, artifacts download API** - `7ee6e63` (feat)
2. **Task 2: Results tab UI — PPA metric cards, layout snapshot, download links, run history table** - `561fd0c` (feat)

**Plan metadata:** (pending — created in final commit)

## Files Created/Modified

- `backend/app/services/metrics_service.py` - parse_ppa_metrics() + MetricsService wrapper
- `backend/app/schemas/artifacts.py` - ArtifactURLs Pydantic schema with optional URL fields
- `backend/app/api/routes/artifacts.py` - GET /jobs/{id}/artifacts with presigned URL generation
- `worker/tasks/tile_generator.py` - Full KLayout PNG generation task (replaces stub); PERMANENT fast-path documented
- `backend/app/main.py` - Registers artifacts router (replaces stub)
- `backend/tests/test_metrics.py` - 5 tests covering parse, fallback, malformed, service wrapper
- `backend/tests/test_artifacts.py` - 4 tests covering 404, schema, URL generation, route registration
- `backend/tests/test_tile_generator.py` - 5 tests covering upload, DB update, klayout-missing fallback, early return, permanence
- `frontend/src/api/artifacts.ts` - getArtifacts() typed API wrapper
- `frontend/src/api/jobs.ts` - Extended RunStatusResponse with config field
- `frontend/src/components/PpaMetricCards/PpaMetricCards.tsx` - 5 metric cards with color thresholds
- `frontend/src/components/LayoutSnapshot/LayoutSnapshot.tsx` - PNG display, VNC button, download links
- `frontend/src/components/RunHistoryTable/RunHistoryTable.tsx` - Clickable run table with status badges and PPA columns
- `frontend/src/pages/RunDetailPage.tsx` - Wired Results tab with PpaMetricCards + LayoutSnapshot + artifact fetching
- `frontend/src/pages/ProjectPage.tsx` - Uses RunHistoryTable component (RSLT-04)

## Decisions Made

- **ORFS METRICS2.1 key names** confirmed from ORFS documentation. Notably `timing__setup__ws` for WNS (not `wns` or `worst_slack`). Integration testing should verify against a real run.
- **generate_png is permanent fast-path** — tile_generator.py has this documented in both module docstring and function docstring per CLAUDE.md constraint.
- **_try_presign() returns None** on ClientError rather than raising — allows partial ArtifactURLs when some artifacts don't yet exist in MinIO.
- **Patch target for tests**: `app.core.config.get_settings` (not `worker.tasks.tile_generator.get_settings`) since `get_settings` is lazily imported inside the function body in tile_generator.py.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed incorrect patch target in tile_generator tests**
- **Found during:** Task 1 (GREEN phase test execution)
- **Issue:** Tests patched `worker.tasks.tile_generator.get_settings` but `get_settings` is imported inside the function body (lazy import), not at module level — patch had no effect
- **Fix:** Changed patch target to `app.core.config.get_settings` which is the actual module where the function lives
- **Files modified:** `backend/tests/test_tile_generator.py`
- **Verification:** All 14 tests pass
- **Committed in:** `7ee6e63` (Task 1 commit)

**2. [Rule 1 - Bug] Extended RunStatusResponse TypeScript interface with config field**
- **Found during:** Task 2 (frontend build)
- **Issue:** RunDetailPage used `run?.config` for the Config tab display but `RunStatusResponse` type had no `config` field, causing 5 TypeScript errors
- **Fix:** Added `config: Record<string, unknown> | null` to `RunStatusResponse` interface in `jobs.ts`
- **Files modified:** `frontend/src/api/jobs.ts`
- **Verification:** `npm run build` exits 0
- **Committed in:** `561fd0c` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs — incorrect mock target, missing TypeScript field)
**Impact on plan:** Both fixes necessary for tests/build to pass. No scope creep.

## Issues Encountered
None beyond the two auto-fixed deviations above.

## User Setup Required
None — no external service configuration required for this plan.

## Next Phase Readiness
- All RSLT-01 through RSLT-04 requirements complete
- LayoutSnapshot has VNC button wired to `onOpenVnc` prop — plan 01-06 implements VNC session start
- Results tab auto-activates on job completion; polling stops on terminal state
- PNG fast-path is documented as permanent and ready for Phase 2 to add tiled viewer alongside it

---
*Phase: 01-core-flow*
*Completed: 2026-03-13*
