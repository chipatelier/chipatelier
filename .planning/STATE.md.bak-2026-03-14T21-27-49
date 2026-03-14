---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: planning
stopped_at: Completed quick/1-add-missing-root-level-documentation/1-PLAN.md
last_updated: "2026-03-14T21:22:33.320Z"
last_activity: 2026-03-14 — Completed quick task 1: Add Missing — Root-level Documentation
progress:
  total_phases: 3
  completed_phases: 1
  total_plans: 8
  completed_plans: 8
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-12)

**Core value:** A student can submit a Verilog design and get a routed layout with metrics — entirely in the browser, on shared university hardware, without installing any tools.
**Current focus:** Phase 1 — Core Flow

## Current Position

Phase: 1 of 3 (Core Flow)
Plan: 0 of 6 in current phase
Status: Ready to plan
Last activity: 2026-03-12 — Roadmap created; requirements mapped; ready to plan Phase 1

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: — min
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01-core-flow P01 | 8 | 2 tasks | 59 files |
| Phase 01-core-flow P02 | 10 | 2 tasks | 17 files |
| Phase 01-core-flow P03 | 15 | 2 tasks | 13 files |
| Phase 01-core-flow P04 | 8 | 2 tasks | 19 files |
| Phase 01-core-flow P05 | 9 | 2 tasks | 18 files |
| Phase 01-core-flow P06 | 9 | 1 tasks | 11 files |
| Phase 01-core-flow P07 | 45 | 3 tasks | 21 files |
| Phase 01-core-flow P08 | 13 | 3 tasks | 10 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: SKY130 only for MVP; GF180/ASAP7 deferred to Phase 2 (no arch changes needed)
- [Init]: Pin ORFS image version; canary CI hardened in Phase 2, not Phase 1
- [Init]: Dedicated Celery worker processes for orfs_jobs vs background tasks (not routing modes)
- [Init]: Fast-path single PNG is a permanent path — never merged with tile generation pipeline
- [Init]: VNC token = HMAC-signed JWT with separate VNC_TOKEN_SECRET (not session UUID)
- [Research]: Replace python-jose → PyJWT 2.10.x; replace passlib → argon2-cffi 25.x
- [Phase 01-core-flow]: JSONBCompatible TypeDecorator uses JSONB on PostgreSQL and falls back to JSON on SQLite for test isolation
- [Phase 01-core-flow]: ppa and config are separate JSONB columns on runs table — ppa holds metrics only, config holds config.mk snapshot
- [Phase 01-core-flow]: Two dedicated Celery worker processes (orfs-worker for orfs_jobs, background-worker for tiles/VNC/grading) — architectural lock, never merge
- [Phase 01-core-flow]: Cookie path set to /api/v1/auth (not /api/v1/auth/refresh) — covers both logout and refresh while keeping cookie away from general API routes
- [Phase 01-core-flow]: TestClient cookie helper pattern: extract Set-Cookie header and pass cookies= kwarg explicitly in logout/refresh tests; do not rely on automatic cookie jar forwarding
- [Phase 01-core-flow]: Use app.dependency_overrides not mock.patch for FastAPI dependencies in tests — FastAPI captures function reference at route registration time
- [Phase 01-core-flow]: Import Celery tasks inside route handler body to break circular imports between backend/ and worker/; patch at worker.tasks.orfs_job level in tests
- [Phase 01-core-flow]: storage_opt size= commented out in ContainerManager — overlay2 + pquota mount option not guaranteed on RHEL/Rocky 9; disk quotas at OS level as alternative
- [Phase 01-core-flow]: WS router registered at /api/v1/ws prefix (separate from /api/v1/jobs) to avoid path ambiguity between WS and REST job routes
- [Phase 01-core-flow]: useLogStream uses autoScrollRef (not state) for scroll tracking to avoid stale closure in xterm onScroll callback
- [Phase 01-core-flow]: Results tab locked (disabled) while run is active — auto-switches on complete via polling
- [Phase 01-core-flow]: ORFS METRICS2.1 key names used in parse_ppa_metrics: timing__setup__ws for WNS — verify against real ORFS run during integration testing
- [Phase 01-core-flow]: generate_png permanent fast-path documented in tile_generator.py; Phase 2 tiled viewer must not remove PNG path (CLAUDE.md constraint)
- [Phase 01-core-flow]: Artifacts endpoint uses _try_presign() returning None on ClientError for missing artifacts — allows partial presigned URL responses
- [Phase 01-core-flow]: Global VNC session limit checked before idempotency lookup to ensure MAX_VNC_SESSIONS always enforced
- [Phase 01-core-flow]: VNC token passed to Nginx validation subrequest via X-VNC-Token header (not query string) to prevent token appearing in access.log
- [Phase 01-core-flow]: Three-queue Celery: high_priority for instructor/admin, orfs_jobs for students via fair queue, background for tiles/VNC — orfs-worker consumes both high_priority and orfs_jobs
- [Phase 01-core-flow]: Fair queue scoring: score = student queue depth at submission (ZADD ZPOPMIN); students with fewer queued runs get lower scores and dispatched first
- [Phase 01-core-flow]: Warm pool target = WARM_POOL_SIZE/2; claim returns None gracefully on miss/stale; replenish called in finally block and on 30s beat
- [Phase 01-core-flow]: Auto-retry: max_retries=1 on DockerException only; non-zero exit code (design error) NOT retried — user must fix Verilog/SDC
- [Phase 01-core-flow]: Notes privacy: notes excluded from RunSummary (list); only visible in RunStatusResponse to run owner; PATCH /runs/{id}/notes is owner-only (403 for others)
- [Phase 01-core-flow]: Inline redis zadd/incr logic in jobs.py student path — eliminates cross-container worker package import
- [Phase 01-core-flow]: worker.celery_app uses try/except config_from_object(worker.celeryconfig) with fallback to celeryconfig for production CWD
- [Phase 01-core-flow]: VNC start_session.sh uses ORFS open.tcl with ODB_FILE + DESIGN_CONFIG; VNC_ODB_PATH replaces VNC_DEF_PATH
- [Phase 01-core-flow]: parse_ppa_metrics returns (ppa, stage_metrics) tuple; iterates per-stage ORFS JSON files; stage_metrics written to DB

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1]: CPU budget on DL380 Gen9 is tight (28-36 cores) — profile realistic mixed workload before Phase 2 ships
- [Phase 1]: Orphaned container watchdog must be built alongside job pipeline, not after
- [Phase 2]: PostgreSQL JSONB leaderboard ordering requires functional B-tree index with ::numeric cast, not GIN

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Add Missing — Root-level Documentation | 2026-03-14 | 7f22e3f | [1-add-missing-root-level-documentation](./quick/1-add-missing-root-level-documentation/) |

## Session Continuity

Last session: 2026-03-14T21:22:33.317Z
Stopped at: Completed quick/1-add-missing-root-level-documentation/1-PLAN.md
Resume file: None
