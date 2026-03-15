---
phase: 02-learning-layer
plan: "05"
subsystem: layout-inspect
tags: [backend, frontend, openroad, sqlite, query, react, typescript]
requirements: [LAYT-02]

dependency_graph:
  requires: [02-01]
  provides: [layout-click-inspect]
  affects: [frontend-layout-viewer, backend-query-api]

tech_stack:
  added:
    - "OpenROAD subprocess query via docker run (read-only, --network none)"
    - "StorageService.download_file() — download ODB from MinIO to temp dir"
    - "uuid.UUID path parameter type in FastAPI route for SQLite compatibility"
  patterns:
    - "Linear ODB instance scan (no spatial index — per RESEARCH.md Pitfall 2)"
    - "Y-axis inversion formula: yUm = (1 - clickY/H) * (ymax - ymin) + ymin"
    - "tempfile.mkdtemp + shutil.rmtree in finally block for guaranteed cleanup"
    - "InspectSidebar renders null until first query (not empty state)"

key_files:
  created:
    - backend/app/api/routes/query.py
    - backend/app/schemas/query.py
    - frontend/src/api/query.ts
    - frontend/src/components/LayoutSnapshot/InspectSidebar.tsx
  modified:
    - backend/app/main.py
    - backend/app/services/storage_service.py
    - frontend/src/components/LayoutSnapshot/LayoutSnapshot.tsx
    - backend/tests/test_query.py

decisions:
  - "uuid.UUID path parameter (not str) required for SQLite test compatibility — UUID column type expects uuid.UUID object, string causes AttributeError on .hex"
  - "Ownership check uses run.project.user_id != current_user.id UUID comparison (not string cast) — works with SQLAlchemy UUID objects"
  - "LayoutBbox exported as named interface from LayoutSnapshot.tsx for consumers"
  - "InspectSidebar uses dark theme inline styles consistent with existing LayoutSnapshot styling (no Tailwind — not in this project)"

metrics:
  duration_minutes: 12
  tasks_completed: 2
  files_created: 4
  files_modified: 4
  tests_added: 4
  completed_date: "2026-03-15"
---

# Phase 2 Plan 05: Click-to-Inspect Layout Summary

**One-liner:** Layout click-to-inspect via OpenROAD subprocess ODB scan with Y-axis-inverted pixel→micron coordinate mapping and persistent InspectSidebar.

## What Was Built

### Backend — GET /api/v1/query/{run_id}

`backend/app/api/routes/query.py` implements the click-to-inspect endpoint:

1. Validates run ownership (403 for non-owners)
2. Checks artifact_path is set (400 for incomplete runs)
3. Downloads the highest completed stage ODB from MinIO to a temp directory
4. Runs OpenROAD inside the ORFS container image with a Python script that performs a **linear bounding-box scan** of all instances (no spatial index — per RESEARCH.md Pitfall 2, queryRegion does not exist in OpenDB)
5. Returns matching elements as `[{name, master, nets}]` — empty list when nothing found (not a 404)
6. Cleans up temp directory in `finally` block — no ODB files left on disk

Security: `--network none`, `--cap-drop ALL`, `--security-opt no-new-privileges`, read-only volume mount, 30-second timeout.

`backend/app/schemas/query.py` defines `InspectElement` and `InspectResponse` Pydantic models.

`backend/app/services/storage_service.py` — added `download_file()` method using boto3 `download_file`.

### Frontend — LayoutSnapshot + InspectSidebar

`frontend/src/api/query.ts` — typed `clickToInspect()` function using the shared axios client.

`frontend/src/components/LayoutSnapshot/InspectSidebar.tsx`:
- Renders null when `elements === null` and not loading (hidden until first click)
- Shows "No element at this location" on empty list
- Shows element name (monospace), master cell type, and net tags
- Persists until user clicks the X dismiss button

`frontend/src/components/LayoutSnapshot/LayoutSnapshot.tsx` extensions:
- New `layoutBbox?: LayoutBbox` prop (xmin/ymin/xmax/ymax in microns)
- `handleImageClick` maps pixel → micron coordinates with Y-axis inversion:
  - `xUm = (clickX / W) * (bbox.xmax - bbox.xmin) + bbox.xmin`
  - `yUm = (1 - clickY / H) * (bbox.ymax - bbox.ymin) + bbox.ymin`
- Crosshair cursor on image when inspect mode active
- InspectSidebar displayed alongside image in a flex row
- All existing VNC launcher + download links unchanged (CLAUDE.md requirement)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed UUID path parameter type for SQLite compatibility**
- **Found during:** Task 1 GREEN phase (tests returning 500)
- **Issue:** Route defined `run_id: str`, but SQLAlchemy UUID column type (used in SQLite tests) requires a `uuid.UUID` object — passing a string caused `AttributeError: 'str' object has no attribute 'hex'`
- **Fix:** Changed path parameter to `run_id: uuid.UUID`; FastAPI's path parameter parsing automatically coerces the URL string to UUID
- **Files modified:** `backend/app/api/routes/query.py`
- **Commit:** 97e34be

**2. [Rule 2 - Missing functionality] Added StorageService.download_file() method**
- **Found during:** Task 1 implementation
- **Issue:** `storage_service.py` had upload, presigned URL, and delete_prefix but no download method — required by the query endpoint to fetch ODB from MinIO
- **Fix:** Added `download_file(key, local_path)` using boto3 `download_file`
- **Files modified:** `backend/app/services/storage_service.py`
- **Commit:** 97e34be

## Tests

4 new tests in `backend/tests/test_query.py`:
- `test_click_to_inspect_hit` — mocked subprocess returns one element
- `test_click_to_inspect_miss` — mocked subprocess returns empty list
- `test_query_non_owner_run_returns_403` — subprocess not called for unauthorized access
- `test_query_run_without_artifacts_returns_400` — 400 for runs without artifact_path

All 4 tests pass. Full suite: 165 passed, 3 pre-existing failures in test_tile_generator.py (unrelated to this plan).

## Self-Check: PASSED
