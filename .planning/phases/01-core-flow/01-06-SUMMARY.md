---
phase: 01-core-flow
plan: "06"
subsystem: vnc
tags: [vnc, novnc, websocket, nginx, auth_request, openroad, jwt, docker, supervisor]

# Dependency graph
requires:
  - phase: 01-core-flow plan 01-02
    provides: create_vnc_token(user_id, run_id, port) signing with VNC_TOKEN_SECRET; decode_token with secret override
  - phase: 01-core-flow plan 01-04
    provides: Run model with artifact_path, VncSession model, job lifecycle infrastructure
  - phase: 01-core-flow plan 01-05
    provides: LayoutSnapshot component with onOpenVnc hook, artifact_path on completed runs
provides:
  - POST /api/v1/vnc/start/{runId}: spawns VNC container, returns HMAC-signed JWT token (VNC_TOKEN_SECRET)
  - GET /api/v1/vnc/validate?token=...: Nginx auth_request endpoint, returns X-VNC-Port header
  - DELETE /api/v1/vnc/{sessionId}: stops container, marks session stopped
  - chipatelier/vnc-viewer Docker image: openroad/orfs + Xvfb + x11vnc + websockify + supervisor
  - vnc-container/start_session.sh: Tcl read_lef/read_def + gui::show for DEF pre-load
  - Nginx VNC proxy: auth_request validation before WebSocket proxy to container port
  - frontend/src/api/vnc.ts: typed startVncSession/stopVncSession API client
  - LayoutSnapshot VNC button: calls startVncSession, opens vnc_url in new browser tab
  - DASH-04: storage usage display already present in ProjectListPage (built in plan 01-03)
affects:
  - Phase 2 tiled viewer (must not break VNC session endpoints)
  - Nginx config updates (VNC routing is now active)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - VNC token in URL path (not query string) to prevent Nginx access.log exposure
    - Nginx auth_request with internal /vnc-validate location passing token via X-VNC-Token header
    - MAX_VNC_SESSIONS global limit checked BEFORE idempotency check to ensure limit always enforced
    - start_vnc_container helper separated from Celery task for unit testability
    - supervisord manages Xvfb + x11vnc + websockify + OpenROAD with priority ordering (10/20/30/40)

key-files:
  created:
    - backend/app/api/routes/vnc.py
    - backend/app/schemas/vnc.py
    - vnc-container/Dockerfile
    - vnc-container/supervisord.conf
    - vnc-container/start_session.sh
    - frontend/src/api/vnc.ts
  modified:
    - worker/tasks/vnc_session.py
    - infra/nginx/nginx.conf
    - docker-compose.yml
    - backend/app/main.py
    - frontend/src/components/LayoutSnapshot/LayoutSnapshot.tsx
    - backend/tests/test_vnc.py

key-decisions:
  - "Global VNC session limit (MAX_VNC_SESSIONS) checked before idempotency lookup — ensures limit always enforced even when idempotent return would bypass the count"
  - "Token passed to Nginx /vnc-validate via X-VNC-Token header (set in VNC proxy location), not query string — avoids token in access logs on the auth subrequest path"
  - "start_vnc_container() is a standalone helper function (not inline in Celery task) to enable unit testing with mock_docker without needing async DB context"
  - "VNC containers use docker-compose build-only profile — image is built but never started by compose up; worker spawns them dynamically"

patterns-established:
  - "Pattern: Nginx auth_request for VNC: auth_request /vnc-validate; auth_request_set $vnc_port $upstream_http_x_vnc_port — backend returns port in response header"
  - "Pattern: Internal Nginx location uses proxy_pass http://backend/api/v1/vnc/validate?token=$http_x_vnc_token to forward token as query param"
  - "Pattern: VNC token type='vnc', signed with separate VNC_TOKEN_SECRET — decode_token(token, secret=settings.VNC_TOKEN_SECRET) for validation"

requirements-completed: [LAYT-01, DASH-04]

# Metrics
duration: 23min
completed: 2026-03-13
---

# Phase 1 Plan 06: VNC Viewer Session API and Nginx Token Proxy Summary

**noVNC container lifecycle with HMAC-signed VNC tokens, Nginx auth_request validation before WebSocket proxy, DEF pre-load via OpenROAD Tcl, and MAX_VNC_SESSIONS enforcement**

## Performance

- **Duration:** 23 min
- **Started:** 2026-03-13T08:49:00Z
- **Completed:** 2026-03-13T08:51:34Z
- **Tasks:** 1 of 2 (Task 1 complete; Task 2 is a human-verify checkpoint — awaiting verification)
- **Files modified:** 11

## Accomplishments

- VNC session API with three endpoints: start (201 + token), validate (200 + X-VNC-Port), and stop (204)
- VNC token signed with VNC_TOKEN_SECRET (separate from JWT_SECRET_KEY) — decoded by Nginx subrequest before proxying
- Nginx auth_request pattern fully configured: internal /vnc-validate location + /vnc/{token}/... proxy block
- noVNC container image defined: openroad/orfs:latest with Xvfb + x11vnc + websockify + OpenROAD GUI
- DEF pre-load via OpenROAD Tcl scripting: read_lef/read_def sequence + gui::show in start_session.sh
- MAX_VNC_SESSIONS (default 8) enforced with 429 response; port range 6080-6099 allocated from DB
- Frontend LayoutSnapshot button wired to startVncSession() API — opens /vnc/{token} in new tab

## Task Commits

1. **Test (TDD RED): VNC session API failing tests** - `9a5eb6b` (test)
2. **Task 1: VNC session API + container lifecycle implementation** - `dfe4275` (feat)

## Files Created/Modified

- `backend/app/api/routes/vnc.py` — POST /vnc/start, GET /vnc/validate (Nginx auth_request), DELETE /vnc/{id}
- `backend/app/schemas/vnc.py` — VncStartResponse, VncSessionResponse Pydantic models
- `backend/app/main.py` — registered VNC router at /api/v1
- `worker/tasks/vnc_session.py` — start_vnc Celery task + start_vnc_container helper with VNC_DEF_PATH env var
- `vnc-container/Dockerfile` — openroad/orfs:latest + Xvfb + x11vnc + websockify + supervisor
- `vnc-container/supervisord.conf` — process management with priority ordering (xvfb=10, x11vnc=20, websockify=30, openroad=40)
- `vnc-container/start_session.sh` — Tcl read_lef/read_def + gui::show for DEF pre-load on container start
- `infra/nginx/nginx.conf` — /vnc-validate internal location + auth_request VNC proxy block
- `docker-compose.yml` — vnc-viewer build target (build-only profile) + Nginx VNC port range
- `frontend/src/api/vnc.ts` — typed startVncSession() and stopVncSession() API client
- `frontend/src/components/LayoutSnapshot/LayoutSnapshot.tsx` — VNC button calls startVncSession, opens new tab with loading state

## Decisions Made

- Global VNC session limit checked BEFORE idempotency lookup — ensures limit always enforced (test revealed that idempotency check would bypass the count if checked first)
- Token passed to Nginx validation subrequest via `X-VNC-Token` header, not query string — prevents token in Nginx access.log on the auth path
- `start_vnc_container()` extracted as standalone function from Celery task — enables unit testing with mock_docker without async DB setup
- VNC containers use `profiles: [build-only]` in docker-compose — image built but never started directly; worker spawns dynamically

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reordered limit check before idempotency check**
- **Found during:** Task 1 (test_vnc_session_limit test failure)
- **Issue:** Original ordering checked idempotency first; if user had multiple "running" sessions for the same run (as test creates), the idempotency check returned one session before the limit count fired — test expected 429 but got 200
- **Fix:** Moved global count query and 429 guard to execute BEFORE idempotency check; test now passes correctly
- **Files modified:** backend/app/api/routes/vnc.py
- **Verification:** test_vnc_session_limit passes; test_vnc_start_endpoint still passes (idempotency still works when under limit)
- **Committed in:** dfe4275 (implementation commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug fix)
**Impact on plan:** Logic fix ensures limit is always enforced. Idempotency still works correctly when under the session limit.

## Issues Encountered

- None beyond the auto-fixed ordering bug above.

## User Setup Required

None — no external service configuration required beyond existing `.env` variables (`VNC_TOKEN_SECRET`, `MAX_VNC_SESSIONS`) already documented in `.env.example`.

## Next Phase Readiness

- Task 2 is a human-verify checkpoint: requires starting the Docker Compose stack and running through the full Phase 1 end-to-end flow (registration → job submission → logs → results → VNC viewer)
- Once human-verified, Phase 1 (Core Flow) is complete
- Phase 2 can build on: VNC session API (add session listing), VNC URL pattern (stable), storage usage display (already showing in header)

---
*Phase: 01-core-flow*
*Completed: 2026-03-13*
