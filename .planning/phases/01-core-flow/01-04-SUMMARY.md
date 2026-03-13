---
phase: 01-core-flow
plan: "04"
subsystem: ui
tags: [websocket, redis-pubsub, xterm, react, log-streaming, stage-progress, zustand]

requires:
  - phase: 01-core-flow/01-01
    provides: Docker Compose stack, Redis connection pool (get_redis), core settings
  - phase: 01-core-flow/01-02
    provides: JWT auth (decode_token, create_access_token), Zustand auth slice with accessToken
  - phase: 01-core-flow/01-03
    provides: Redis logbuf:{run_id} list + logs:{run_id} channel, RunStatusResponse schema, project/run models

provides:
  - WS endpoint /api/v1/ws/jobs/{run_id}/logs/stream with JWT auth, logbuf replay, pubsub streaming
  - log_parser.py service: detect_stage() and format_stage_separator() for ORFS log analysis
  - GET /jobs/{id}/logs REST endpoint for log history (completed runs)
  - useLogStream hook: WS connection with token auth and 2s reconnect backoff
  - LogTerminal component: xterm.js with scrollback=50000, auto-scroll state machine, Jump to bottom
  - StageStatusBar component: 6-stage ORFS progress bar (synthesis/floorplan/place/cts/route/gds)
  - jobSlice: Zustand slice for stage progress computed from stageCompleted
  - Typed API wrappers: api/projects.ts and api/jobs.ts
  - ProjectListPage: card grid with empty state, storage usage display
  - ProjectPage: run table with PPA columns, file upload, disabled New Run on active run
  - RunDetailPage: tabbed layout with persistent stage bar, 3s polling, auto-switch on completion

affects:
  - 01-05 (layout viewer — builds on run detail page structure)
  - 01-06 (VNC integration — adds new tab to run detail page)

tech-stack:
  added:
    - "@xterm/xterm 5.5.0 — browser terminal emulator with scrollback and ANSI colors"
    - "@xterm/addon-fit — terminal resize to fill container"
    - "fakeredis — async Redis mock for WS endpoint tests"
  patterns:
    - "WS auth via ?token= query param (browsers cannot set custom WS headers)"
    - "Redis logbuf:{run_id} lrange replay before pubsub.listen() for late joiners"
    - "xterm.js auto-scroll state machine: onScroll event, autoScrollRef, showJumpBtn state"
    - "Stage separator detection via startsWith('═══') for distinct terminal styling"
    - "Zustand slice pattern: createJobSlice exported and merged in store/index.ts"
    - "3s polling for active runs with clearInterval on terminal status"

key-files:
  created:
    - backend/app/api/websocket.py
    - backend/app/services/log_parser.py
    - backend/tests/test_websocket.py
    - backend/tests/test_log_parser.py
    - frontend/src/api/projects.ts
    - frontend/src/api/jobs.ts
    - frontend/src/store/jobSlice.ts
    - frontend/src/hooks/useLogStream.ts
    - frontend/src/components/LogTerminal/LogTerminal.tsx
    - frontend/src/components/LogTerminal/index.ts
    - frontend/src/components/StageStatusBar/StageStatusBar.tsx
    - frontend/src/components/StageStatusBar/index.ts
    - frontend/src/pages/ProjectListPage.tsx
    - frontend/src/pages/ProjectPage.tsx
    - frontend/src/pages/RunDetailPage.tsx
  modified:
    - backend/app/api/routes/jobs.py (added GET /jobs/{id}/logs)
    - backend/app/main.py (registered WS router at /api/v1/ws)
    - frontend/src/store/index.ts (merged JobSlice into AppStore)
    - frontend/src/App.tsx (added /projects/:id and /projects/:id/runs/:runId routes)

key-decisions:
  - "WS router registered at /api/v1/ws prefix (not /api/v1) to avoid path ambiguity with REST /jobs routes"
  - "useLogStream uses autoScrollRef (not state) for scroll tracking to avoid stale closure in xterm onScroll callback"
  - "Results tab locked (disabled) while run is active — auto-switches on complete via polling"
  - "StageStatusBar uses CSS @keyframes spin injected via <style> tag (no external CSS dependency)"

patterns-established:
  - "Pattern: TDD for all backend endpoints — RED commit (test), GREEN commit (impl)"
  - "Pattern: WebSocket token auth via query param ?token=; validate before websocket.accept()"
  - "Pattern: pubsub cleanup always in finally block — never orphan Redis subscriptions"
  - "Pattern: LogTerminal connects via useLogStream hook — terminal is display-only, hook handles WS lifecycle"

requirements-completed: [JOB-03, JOB-04]

duration: 8min
completed: 2026-03-13
---

# Phase 1 Plan 04: Log Streaming Pipeline Summary

**Redis pub/sub WebSocket endpoint with logbuf replay for late joiners, xterm.js LogTerminal with locked auto-scroll behavior, 6-stage StageStatusBar, and full project/run navigation pages**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-13T08:19:23Z
- **Completed:** 2026-03-13T08:27:25Z
- **Tasks:** 2
- **Files modified:** 19

## Accomplishments

- JOB-03: WebSocket endpoint at `/api/v1/ws/jobs/{run_id}/logs/stream` replays full logbuf on connect (late joiner support), streams live lines via Redis pub/sub, validates JWT access token via `?token=` query param, cleans up pubsub in finally block — 18 tests pass
- JOB-04: Stage status bar always visible above tabs; stage transitions computed from `stageCompleted` field via Zustand `jobSlice`; separator lines rendered in cyan in xterm terminal; `detect_stage()` identifies all 6 ORFS stages with case-insensitive regex
- xterm.js LogTerminal with `scrollback: 50000`, auto-scroll state machine (onScroll event → autoScrollRef → showJumpBtn), and "Jump to bottom" button; stage separators starting with `═══` styled cyan
- Full project/run navigation: ProjectListPage (card grid with empty state + storage usage), ProjectPage (run table with PPA columns + file upload + disabled New Run on active run), RunDetailPage (tabbed with persistent stage bar, 3s status polling, auto-switch Results tab on completion)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for WS streaming and log parser** - `0037c77` (test)
2. **Task 1 GREEN: WS endpoint, log_parser service, REST log history** - `3f5b98c` (feat)
3. **Task 2: LogTerminal, StageStatusBar, pages, store, API wrappers** - `d15415b` (feat)

## Files Created/Modified

- `backend/app/api/websocket.py` - WS endpoint: JWT auth, lrange replay, pubsub live stream, finally cleanup
- `backend/app/services/log_parser.py` - detect_stage() regex patterns for 6 ORFS stages, format_stage_separator()
- `backend/app/api/routes/jobs.py` - Added GET /jobs/{id}/logs for completed run log history
- `backend/app/main.py` - Registered WS router at /api/v1/ws prefix
- `backend/tests/test_websocket.py` - JOB-03 tests: late joiner, invalid token, pubsub cleanup
- `backend/tests/test_log_parser.py` - JOB-04 tests: all 6 stages, case-insensitive, separator format
- `frontend/src/hooks/useLogStream.ts` - WS hook with reconnect backoff and clean unmount
- `frontend/src/components/LogTerminal/LogTerminal.tsx` - xterm.js with scrollback=50000, auto-scroll, cyan separators
- `frontend/src/components/StageStatusBar/StageStatusBar.tsx` - 6-stage progress bar with spinning icon
- `frontend/src/store/jobSlice.ts` - Zustand slice: stageProgress computed from stageCompleted
- `frontend/src/store/index.ts` - Merged AuthSlice + JobSlice into AppStore
- `frontend/src/api/projects.ts` - Typed wrappers: listProjects, createProject, getProject, listRuns, uploadFiles
- `frontend/src/api/jobs.ts` - Typed wrappers: submitJob, getJobStatus, cancelJob, getLogHistory
- `frontend/src/pages/ProjectListPage.tsx` - Card grid, empty state, storage usage, New Project form
- `frontend/src/pages/ProjectPage.tsx` - Run table, file upload, disabled New Run on active run
- `frontend/src/pages/RunDetailPage.tsx` - Tabbed layout, persistent stage bar, 3s polling, auto-switch
- `frontend/src/App.tsx` - Added /projects/:id and /projects/:id/runs/:runId routes

## Decisions Made

- WS router registered at `/api/v1/ws` prefix (separate from `/api/v1/jobs`) to avoid path ambiguity between WS and REST job routes
- `useLogStream` uses `autoScrollRef` (not React state) for scroll tracking — avoids stale closure in xterm.js `onScroll` callback which fires outside React render cycle
- Results tab locked (disabled, shows "(locked)" label) while run is active — auto-switches via polling when status becomes "complete"
- Stage separator detection uses `startsWith("═══")` rather than regex — matches the separator format published by the Celery worker

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed stale closure in xterm auto-scroll state machine**
- **Found during:** Task 2 (LogTerminal implementation)
- **Issue:** Using React `useState` for `autoScroll` inside xterm `onScroll` callback would create stale closure (xterm callbacks capture initial closure)
- **Fix:** Changed `autoScroll` tracking to `useRef` (`autoScrollRef`) for current value access inside callback; kept `showJumpBtn` as state for React re-render trigger
- **Files modified:** frontend/src/components/LogTerminal/LogTerminal.tsx
- **Verification:** Pattern verified in LogTerminal.tsx — `autoScrollRef.current` used in handleLine, `setShowJumpBtn` triggers button visibility
- **Committed in:** d15415b (Task 2 commit)

**2. [Rule 1 - Bug] Fixed TypeScript unused import errors blocking build**
- **Found during:** Task 2 verification (npm run build)
- **Issue:** App.tsx imported `authLogout`, RunDetailPage.tsx imported duplicate `getProject` and unused `useNavigate` — TypeScript strict mode flags these as errors
- **Fix:** Removed unused imports in App.tsx and RunDetailPage.tsx
- **Files modified:** frontend/src/App.tsx, frontend/src/pages/RunDetailPage.tsx
- **Verification:** `npm run build` exits 0 after fixes
- **Committed in:** d15415b (same Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs)
**Impact on plan:** Both fixes required for correctness. No scope creep.

## Issues Encountered

- xterm.js `onScroll` fires synchronously during scroll but React state updates are batched — required `useRef` for scroll tracking (documented above as auto-fix)
- TestClient `websocket_connect` raises `WebSocketDisconnect` immediately when server closes before accept — test needed to catch this at context manager entry, not inside the `with` block

## User Setup Required

None — no external service configuration required. All services (Redis, PostgreSQL) already configured in prior plans.

## Next Phase Readiness

- Log streaming pipeline is complete: backend WS endpoint + frontend LogTerminal
- Stage progress bar and tabbed run detail page ready for Phase 1.05 (layout viewer integration)
- Run detail page structure designed to accept a new "Layout" tab in Phase 1.05 without refactoring
- VNC tab can be added to RunDetailPage in Phase 1.06 similarly

---
*Phase: 01-core-flow*
*Completed: 2026-03-13*
