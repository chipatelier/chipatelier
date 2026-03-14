---
phase: 01-core-flow
verified: 2026-03-14T12:00:00Z
status: human_needed
score: 15/15 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 10/15
  gaps_closed:
    - "POST /api/v1/jobs/submit returns 202 for student submissions — no worker package imported at request time"
    - "VNC container opens OpenROAD Qt GUI with ODB pre-loaded via ORFS open.tcl using ODB_FILE + DESIGN_CONFIG env vars"
    - "parse_ppa_metrics iterates per-stage JSON files in logs/{platform}/{design}/base/*.json and returns (ppa, stage_metrics) tuple"
    - "stage_metrics JSONB column is written in tile_generator._update_run_record alongside ppa"
    - "tile_generator and vnc_session tasks import from worker.celery_app (not bare celery_app)"
    - "celeryconfig task_routes includes tasks.orfs_job.* wildcard key routing to orfs_jobs queue"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "End-to-end RTL-to-GDS flow: register, create project, upload GCD Verilog, submit job with target_stage=route, watch logs stream"
    expected: "Live log lines appear in xterm.js terminal; stage separator lines like '=== FLOORPLAN ===' appear in cyan; stage status bar advances through synth -> route; Results tab activates on completion with WNS/DRC/power metric cards and layout PNG; download links for GDS, DEF present"
    why_human: "Requires running Docker Compose stack with real ORFS image and real PDK data; cannot verify programmatically"
  - test: "VNC viewer pre-load: after a completed job, click 'Open in VNC viewer'"
    expected: "New browser tab opens showing OpenROAD Qt GUI with the design's ODB layout pre-loaded (not an empty GUI)"
    why_human: "Requires running noVNC container and OpenROAD GUI; visual inspection needed"
  - test: "Stage separator line styling in xterm.js terminal during a live job"
    expected: "Lines matching the stage separator pattern appear in cyan (ANSI escape \\x1b[36m]), visually distinct from regular log lines"
    why_human: "xterm.js rendering and ANSI color escape code processing requires browser visual inspection"
---

# Phase 1: Core Flow Verification Report

**Phase Goal:** A student can submit a Verilog design and watch it compile to a routed layout — entirely in the browser, without installing any tools
**Verified:** 2026-03-14
**Status:** human_needed
**Re-verification:** Yes — after gap closure (Plan 08)

---

## Re-verification Summary

All 5 gaps from the initial verification are confirmed closed in the actual codebase. The full test suite passes: **141/141 tests** (zero regressions). All previously failing tests now pass:

- `test_jobs.py`: 11/11 (was 4/11)
- `test_metrics.py`: 6/6 (updated to per-stage JSON format)
- `test_tile_generator.py`: 5/5 (was 0/5)
- `test_vnc.py`: 8/8 (VNC_ODB_PATH assertion updated)
- `test_task2_infra.py::TestCeleryConfig`: 3/3 (was 2/3)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can register, log in, and stay logged in across browser refreshes; logging out terminates session | VERIFIED | auth.py endpoints pass 55-test suite; httpOnly cookie set on login; Redis jti denylist on logout; Axios 401 interceptor in useTokenRefresh.ts |
| 2 | User can create a project, upload Verilog and config.mk, submit a job, watch live log stream, and see stage-level progress advance | VERIFIED | Project create/upload pass; submit returns 202 (11/11 test_jobs.py pass); log streaming via WebSocket + xterm.js verified; StageStatusBar verified |
| 3 | User can cancel a running job; container stops and status updates to cancelled | VERIFIED | Cancel endpoint wired; status set to 'cancelled'; Celery revoke with SIGTERM; test_cancel_queued_job passes |
| 4 | After job completes, user sees PPA metrics, static layout PNG within seconds, and download links | VERIFIED | parse_ppa_metrics returns (ppa, stage_metrics) tuple from per-stage JSON; tile_generator writes both JSONB columns; presigned URLs via artifacts.py verified |
| 5 | User can launch VNC tab showing OpenROAD GUI with ODB pre-loaded; storage usage in dashboard | VERIFIED | start_session.sh uses ORFS open.tcl with ODB_FILE + DESIGN_CONFIG; VNC session API + Nginx auth_request verified; storage display in ProjectListPage.tsx verified |

**Score:** 5/5 truths verified (all automated checks pass)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docker-compose.yml` | Full service definitions with health checks | VERIFIED | 8 services: postgres, redis, minio, backend, orfs-worker, background-worker, frontend, nginx; dual worker queues correct |
| `backend/alembic/versions/0001_initial_schema.py` | users, projects, runs, vnc_sessions + GIN indexes | VERIFIED | All 4 tables, GIN on ppa/config, functional B-tree on WNS/CLOCK_PERIOD |
| `backend/app/core/config.py` | Settings class with all env vars | VERIFIED | pydantic-settings with lru_cache |
| `worker/celeryconfig.py` | Queue routing with orfs_job.* wildcard | VERIFIED | Wildcard entries `tasks.orfs_job.*` and `worker.tasks.orfs_job.*` at lines 31-32; test_orfs_job_route passes |
| `backend/tests/conftest.py` | Wave 0 pytest fixtures | VERIFIED | async_session, test_client, mock_docker, mock_s3, mock_redis all present |
| `backend/app/core/security.py` | argon2 hash/verify, JWT access/refresh/vnc tokens | VERIFIED | hash_password, verify_password, create_access_token, create_refresh_token, create_vnc_token, decode_token all exported |
| `backend/app/api/deps.py` | get_current_user, require_role | VERIFIED | 62 lines, OAuth2PasswordBearer, role check |
| `backend/app/api/routes/auth.py` | register, login, logout, refresh | VERIFIED | 182 lines, all endpoints implemented |
| `backend/app/api/routes/jobs.py` | submit, status, cancel — no cross-boundary worker import | VERIFIED | Student path inlines Redis zadd/incr (line 120); no `from worker.tasks` import; 11/11 test_jobs.py pass |
| `worker/container/manager.py` | ContainerManager with security constraints | VERIFIED | network_mode=none, cap_drop=ALL, read_only, mem_limit all present (114 lines) |
| `worker/tasks/orfs_job.py` | Full ORFS task with lifecycle | VERIFIED | 303 lines; stage detection, Redis publish, finally cleanup |
| `backend/app/services/metrics_service.py` | PPA parsing from ORFS per-stage JSON, (ppa, stage_metrics) tuple | VERIFIED | Iterates logs/{platform}/{design}/base/*.json via sorted glob; correct ORFS key format (route__timing__setup__ws); returns tuple; 6/6 test_metrics.py pass |
| `worker/tasks/tile_generator.py` | KLayout PNG generation, stage_metrics written to DB | VERIFIED | try/except worker.celery_app import; _update_run_record writes both ppa and stage_metrics JSONB columns; 5/5 test_tile_generator.py pass |
| `backend/app/api/routes/artifacts.py` | Presigned URLs for artifacts | VERIFIED | generate_download_url used for gds/png/odb (79 lines) |
| `backend/app/api/websocket.py` | WS endpoint with log replay + pubsub | VERIFIED | lrange replay then pubsub.listen; JWT validated via ?token= query param |
| `frontend/src/hooks/useLogStream.ts` | WebSocket hook with auto-reconnect | VERIFIED | 93 lines; new WebSocket, reconnect on close |
| `frontend/src/components/LogTerminal/LogTerminal.tsx` | xterm.js, scrollback=50000, Jump to bottom | VERIFIED | scrollback=50000, autoScrollRef, showJumpBtn, cyan separator lines |
| `frontend/src/components/StageStatusBar/StageStatusBar.tsx` | 6-stage progress bar | VERIFIED | 136 lines; done/running/pending states |
| `frontend/src/pages/RunDetailPage.tsx` | Tabbed layout, Results/Logs/Config | VERIFIED | 365 lines, tabbed layout, Results tab disabled during run |
| `frontend/src/pages/ProjectListPage.tsx` | Card grid, storage usage | VERIFIED | DASH-04: storage_used_bytes displayed as "X.X GB of 5 GB used" |
| `frontend/src/hooks/useTokenRefresh.ts` | Axios 401 interceptor | VERIFIED | interceptors.response, refresh token queue |
| `vnc-container/start_session.sh` | ODB pre-load via ORFS open.tcl | VERIFIED | Uses `exec $OPENROAD_EXE -gui /OpenROAD-flow-scripts/flow/scripts/open.tcl`; ODB_FILE set from VNC_ODB_PATH; no read_lef/read_def |
| `backend/alembic/versions/0002_pgvector_and_queue_tables.py` | pgvector + queue_priority column | VERIFIED | Plan 07 migration exists and correct |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/core/database.py` | postgresql+asyncpg | create_async_engine(settings.DATABASE_URL) | VERIFIED | confirmed in database.py |
| `worker/celery_app.py` | redis | broker=settings.REDIS_URL | VERIFIED | celery_app.py imports and uses REDIS_URL |
| `backend/alembic/env.py` | async engine | run_async_migrations + AsyncConnection | VERIFIED | asyncio.run pattern in env.py |
| `backend/app/api/routes/auth.py (login)` | response.set_cookie | httponly=True, path=/api/v1/auth/refresh | VERIFIED | line 95 confirmed |
| `backend/app/api/routes/auth.py (logout)` | Redis SET with TTL | denylist refresh token jti | VERIFIED | redis.set(f"denylist:{jti}") |
| `frontend/src/hooks/useTokenRefresh.ts` | POST /api/v1/auth/refresh | axios interceptor on 401 | VERIFIED | interceptors.response.use line 48 |
| `backend/app/api/routes/jobs.py (submit, student path)` | Redis fair_queue:normal sorted set | redis_lib.Redis.from_url().zadd() | VERIFIED | line 120: r.zadd(queue_key, {str(run.id): score}) — no worker package import |
| `worker/tasks/orfs_job.py` | ContainerManager.run_container | try/finally block | VERIFIED | finally: block at line 234 removes container |
| `worker/tasks/orfs_job.py` | Redis PUBLISH logs:{run_id} | log streaming per line | VERIFIED | r.publish in publish_line function |
| `backend/app/api/websocket.py` | Redis logbuf:{run_id} | lrange replay then pubsub.listen() | VERIFIED | line 51: r.lrange(f"logbuf:{run_id}") |
| `frontend/src/hooks/useLogStream.ts` | ws://host/api/v1/jobs/{id}/logs/stream | new WebSocket | VERIFIED | line 49: new WebSocket(url) |
| `frontend/src/components/LogTerminal/LogTerminal.tsx` | useLogStream hook | onLine callback + term.writeln | VERIFIED | term.writeln called in handleLine |
| `worker/tasks/orfs_job.py` | worker.tasks.tile_generator.generate_png.delay | dispatched after exit_code==0 | VERIFIED | line 220-221: generate_png.delay(run_id, workspace) |
| `worker/tasks/tile_generator.py` | MinIO runs/{run_id}/layout.png | s3.put_object | VERIFIED | line 141-148: puts to runs/{run_id}/layout.png |
| `worker/tasks/tile_generator.py` | stage_metrics JSONB column | _update_run_record SQL: stage_metrics = CAST(:sm AS jsonb) | VERIFIED | line 206: explicit CAST(:sm AS jsonb) in UPDATE statement |
| `backend/app/services/metrics_service.py` | logs/{platform}/{design}/base/*.json | sorted(logs_dir.glob("*.json")) | VERIFIED | line 42: per-stage file iteration confirmed |
| `backend/app/api/routes/artifacts.py` | storage_service.generate_download_url | boto3 presigned URL | VERIFIED | line 28: generate_download_url |
| `backend/app/api/routes/vnc.py (start)` | create_vnc_token(user_id, run_id, port) | VNC_TOKEN_SECRET signed JWT | VERIFIED | line 150: create_vnc_token called |
| `infra/nginx/nginx.conf (/vnc/{token})` | GET /api/v1/vnc/validate?token | auth_request directive | VERIFIED | auth_request /vnc-validate at line 70-71 |
| `vnc-container/start_session.sh` | $OPENROAD_EXE -gui /OpenROAD-flow-scripts/flow/scripts/open.tcl | ODB_FILE + DESIGN_CONFIG env vars set | VERIFIED | line 21: exec with open.tcl; ODB_FILE set from VNC_ODB_PATH env var |
| `worker/tasks/vnc_session.py` | VNC_ODB_PATH env var in container | STAGE_ODB map resolution | VERIFIED | line 64: VNC_ODB_PATH in environment dict; no VNC_DEF_PATH |
| `worker/tasks/tile_generator.py` | from worker.celery_app import app | try/except with fallback | VERIFIED | lines 15-18: try worker.celery_app, except ImportError fallback |
| `worker/tasks/vnc_session.py` | from worker.celery_app import app | try/except with fallback | VERIFIED | lines 4-7: try worker.celery_app, except ImportError fallback |
| `worker/celeryconfig.py` | tasks.orfs_job.* wildcard | task_routes dict entry | VERIFIED | lines 31-32: both tasks.orfs_job.* and worker.tasks.orfs_job.* present |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| AUTH-01 | 01-02 | User can create account with email/password | SATISFIED | POST /register creates user with argon2id; test_auth.py passes |
| AUTH-02 | 01-02 | JWT access token + httpOnly refresh cookie | SATISFIED | Login sets cookie httponly=True at /api/v1/auth/refresh |
| AUTH-03 | 01-02 | Logout invalidates refresh cookie | SATISFIED | jti added to Redis denylist; cookie cleared |
| AUTH-04 | 01-02 | Session persists across browser refresh via automatic access token renewal | SATISFIED | Axios interceptor in useTokenRefresh.ts queues retries on 401 |
| JOB-01 | 01-01, 01-03 | Create project and upload Verilog/config.mk | SATISFIED | POST /projects and /upload endpoints; 4 project tests pass |
| JOB-02 | 01-01, 01-03, 01-07, 01-08 | Submit job runs ORFS in isolated Docker container | SATISFIED | ContainerManager with all security constraints; submit returns 202; 11/11 test_jobs.py pass; no cross-boundary import |
| JOB-03 | 01-04 | Live log streaming in xterm.js | SATISFIED | WebSocket endpoint, Redis pub/sub, xterm.js LogTerminal all verified |
| JOB-04 | 01-03, 01-04, 01-07, 01-08 | Stage-level progress visible | SATISFIED | StageStatusBar component verified; status polling in RunDetailPage; submit no longer 500 |
| JOB-05 | 01-03, 01-08 | User can cancel running job | SATISFIED | Cancel endpoint wired; SIGTERM revoke; test_cancel_queued_job passes |
| RSLT-01 | 01-05, 01-08 | PPA metrics parsed from ORFS reports | SATISFIED | metrics_service reads per-stage JSON (route__timing__setup__ws etc.); returns (ppa, stage_metrics) tuple; stage_metrics written to DB; 6/6 test_metrics.py pass |
| RSLT-02 | 01-05 | Download links for GDS, DEF, timing reports | SATISFIED | artifacts.py generates presigned URLs; ArtifactURLs schema correct |
| RSLT-03 | 01-05, 01-08 | Static layout PNG within seconds of job completion | SATISFIED | KLayout PNG task; import fixed (worker.celery_app); _update_run_record writes stage_metrics; 5/5 test_tile_generator.py pass |
| RSLT-04 | 01-03, 01-05, 01-07 | Run history table with PPA metrics | SATISFIED | RunHistoryTable component; listRuns API; RunSummary includes ppa field |
| LAYT-01 | 01-06, 01-08 | VNC viewer opens OpenROAD GUI with ODB pre-loaded | SATISFIED | start_session.sh uses ORFS open.tcl (exec with ODB_FILE + DESIGN_CONFIG); vnc_session.py passes VNC_ODB_PATH via STAGE_ODB map; Nginx auth_request verified |
| DASH-04 | 01-02, 01-06 | Storage usage displayed in dashboard | SATISFIED | ProjectListPage.tsx: "X GB of 5 GB used" wired to user.storage_used_bytes |

**Satisfied:** 15/15 fully satisfied
**Partial:** 0/15
**Failed:** 0/15

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | Zero blockers or warnings found in gap-closure files |

Note: The `except Exception` fallback in `jobs.py` student path (lines 122-134) is intentional — it gracefully handles test environments without Redis mock. The comment makes this clear. Not a defect.

---

## Human Verification Required

### 1. End-to-end RTL-to-GDS flow

**Test:** After running `docker compose up -d`, register a new user, create a project, upload GCD Verilog source files and a config.mk, submit a job with target_stage=route, and observe the result in the browser.
**Expected:** Live log lines appear in xterm.js terminal; stage separator lines (e.g., "=== FLOORPLAN ===") appear in cyan; stage status bar advances from synth through route; Results tab activates on completion showing WNS, TNS, DRC count, core area, power metric cards and a layout PNG; download links for GDS and DEF are present.
**Why human:** Requires running Docker Compose stack with the real ORFS image (openroad/orfs:latest), real PDK data mounted at PDK_ROOT, and CPU/memory resources for the ORFS flow. Cannot be verified programmatically.

### 2. VNC viewer pre-load (after Gap 2 fix)

**Test:** After a job completes successfully, click "Open in VNC viewer" on the run detail page.
**Expected:** A new browser tab opens showing the OpenROAD Qt GUI with the design's completed ODB layout pre-loaded. The GUI should display the routed layout, not an empty OpenROAD window.
**Why human:** Requires running the noVNC container (chipatelier/vnc-viewer:latest image) and the OpenROAD GUI with X11/Xvfb. Visual inspection of the GUI content is needed to confirm ODB loading succeeded.

### 3. Stage separator line styling in xterm.js

**Test:** During a live job run, observe the xterm.js terminal in the browser.
**Expected:** Lines matching the stage separator pattern appear in cyan (ANSI escape `\x1b[36m`), visually distinct from regular white log output.
**Why human:** xterm.js rendering and ANSI color escape code processing requires visual inspection in a browser. Terminal color output cannot be verified by examining source code alone.

---

## Gaps Summary

No gaps remain. All 5 previously identified gaps are closed:

- **Gap 1 (jobs.py HTTP 500):** Closed. Backend route now inlines Redis zadd/incr logic directly using `redis_lib.Redis.from_url()`. The `from worker.tasks.fair_queue import enqueue_student_job` cross-boundary import is gone. Fallback to Celery send_task when Redis is unavailable handles test environments cleanly.

- **Gap 2 (VNC wrong DEF loading):** Closed. `start_session.sh` now uses ORFS `open.tcl` invocation: sets `ODB_FILE` from `VNC_ODB_PATH` env var, sets `DESIGN_CONFIG`, and executes `$OPENROAD_EXE -gui /OpenROAD-flow-scripts/flow/scripts/open.tcl`. The `read_lef`/`read_def` inline Tcl approach is gone. `vnc_session.py` passes `VNC_ODB_PATH` resolved via `STAGE_ODB` map.

- **Gap 3 (metrics wrong file format):** Closed. `metrics_service.py` iterates `logs/{platform}/{design}/base/*.json` in sorted order, merges into `stage_metrics`, then maps ORFS key format (`route__timing__setup__ws` etc.) to friendly PPA names. Returns `(ppa, stage_metrics)` tuple. `tile_generator._update_run_record` writes both JSONB columns to the database.

- **Gap 4 (worker bare imports):** Closed. `tile_generator.py` and `vnc_session.py` both use `try: from worker.celery_app import app; except ImportError: from celery_app import app` pattern. `worker/celery_app.py` also uses the same try/except for `config_from_object`. All tile_generator and VNC tests pass.

- **Gap 5 (Celery wildcard routing):** Closed. `celeryconfig.py` now contains `"tasks.orfs_job.*": {"queue": "orfs_jobs"}` and `"worker.tasks.orfs_job.*": {"queue": "orfs_jobs"}` entries alongside the existing explicit task name entries. `TestCeleryConfig::test_orfs_job_route` passes.

**Remaining work:** Human verification of the end-to-end browser flow against a live Docker Compose stack. All automated checks pass.

---

_Verified: 2026-03-14_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes — initial verification 2026-03-14, gap closure via Plan 08_
