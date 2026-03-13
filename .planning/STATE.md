---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: planning
stopped_at: Completed 01-core-flow plan 01-03 (Job Pipeline)
last_updated: "2026-03-13T08:17:49.050Z"
last_activity: 2026-03-12 — Roadmap created; requirements mapped; ready to plan Phase 1
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 6
  completed_plans: 3
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

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1]: CPU budget on DL380 Gen9 is tight (28-36 cores) — profile realistic mixed workload before Phase 2 ships
- [Phase 1]: Orphaned container watchdog must be built alongside job pipeline, not after
- [Phase 2]: PostgreSQL JSONB leaderboard ordering requires functional B-tree index with ::numeric cast, not GIN

## Session Continuity

Last session: 2026-03-13T08:17:49.047Z
Stopped at: Completed 01-core-flow plan 01-03 (Job Pipeline)
Resume file: None
