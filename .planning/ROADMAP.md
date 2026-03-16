# Roadmap: ChipAtelier

## Overview

ChipAtelier ships in three phases that build on each other. Phase 1 delivers the full
RTL-to-GDS pipeline in the browser — auth, job execution, live logs, artifacts, and VNC
viewer. Phase 2 adds the learning layer that makes ChipAtelier a course platform —
assignments, grading, config editor, leaderboard, and instructor tooling. Phase 3 adds
AI assistance (log explainer, config advisor, context-aware chat) that elevates the platform
from a tool into a tutor.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Core Flow** - Full RTL-to-GDS pipeline in the browser: auth, job execution, live logs, artifacts, VNC viewer, and storage visibility (completed 2026-03-13)
- [x] **Phase 2: Learning Layer** - Course and assignment system, config editor, click-to-inspect layout, leaderboard, run comparison, and instructor dashboard (completed 2026-03-15)
- [ ] **Phase 3: AI Assistance** - Local Ollama-powered log explainer, config advisor, and context-aware chat — design data stays on-premise

## Phase Details

### Phase 1: Core Flow
**Goal**: A student can submit a Verilog design and watch it compile to a routed layout — entirely in the browser, without installing any tools
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, JOB-01, JOB-02, JOB-03, JOB-04, JOB-05, RSLT-01, RSLT-02, RSLT-03, RSLT-04, LAYT-01, DASH-04
**Success Criteria** (what must be TRUE):
  1. User can register, log in, and stay logged in across browser refreshes; logging out from any page terminates the session
  2. User can create a project, upload Verilog and config.mk, submit a job, watch live log output stream in a browser terminal, and see stage-level progress advance through synthesis → route → gds
  3. User can cancel a running job; the container stops and the job status updates to cancelled
  4. After a job completes, user sees PPA metrics (WNS, TNS, DRC count, area, power), a static layout PNG within seconds, and download links for GDS, DEF, and timing reports
  5. User can launch a VNC tab that opens the OpenROAD Qt GUI with their completed DEF pre-loaded; user sees their current storage usage in the dashboard
**Plans**: 8 plans

Plans:
- [ ] 01-01-PLAN.md — Infrastructure (Docker Compose, DB schema, Alembic migrations, Celery queue architecture, pytest Wave 0)
- [ ] 01-02-PLAN.md — Authentication (register, login, JWT + httpOnly refresh cookie, session renewal, logout, storage display)
- [ ] 01-03-PLAN.md — Job pipeline (project create, file upload, ORFS container lifecycle, cgroup limits, orphaned-container watchdog)
- [ ] 01-04-PLAN.md — Log streaming + navigation UI (Redis pub/sub, WebSocket, xterm.js, StageStatusBar, project/run pages)
- [ ] 01-05-PLAN.md — Artifacts and results (KLayout PNG generation, PPA metrics parsing, presigned downloads, Results tab)
- [ ] 01-06-PLAN.md — VNC viewer (noVNC container, HMAC-signed token, Nginx auth_request proxy, DEF pre-load) — Docker Compose stack, database schema, Alembic migrations, Celery queue architecture (dedicated orfs_jobs + background workers)
- [ ] 01-07-PLAN.md — v2 spec gaps: pgvector extension, fair per-student queue (Redis sorted sets), high-priority queue (instructor/admin), container warm pool, failure auto-retry, run notes (private by default), AI service colocation in backend
- [ ] 01-08-PLAN.md — Gap closure: fix jobs.py cross-boundary import (HTTP 500), start_session.sh open.tcl VNC loading, metrics_service per-stage JSON parsing with (ppa, stage_metrics) tuple, celery_app import paths, celeryconfig wildcard routes
- [ ] 01-09-PLAN.md — Gap closure: ORFS invocation (WORK_HOME, --file flag, target_stage, no PDK_ROOT, read_only=False, tmpfs=2g), metrics key names (globalroute__, detailedroute__route__drc_errors), stage detection via flow.sh pattern, GRT failure detection

### Phase 2: Learning Layer
**Goal**: Instructors can run a course on ChipAtelier — creating assignments with locked parameters and checkpoint rules — and students can submit for auto-graded scores with leaderboard ranking
**Depends on**: Phase 1
**Requirements**: COUR-01, COUR-02, COUR-03, COUR-04, COUR-05, EDIT-01, EDIT-02, LAYT-02, DASH-01, DASH-02, DASH-03
**Success Criteria** (what must be TRUE):
  1. Instructor can create a course, generate a human-readable enrollment code (VLSI-YYYY-XXXX), and create an assignment specifying locked/editable parameters, checkpoint rules, and due date
  2. Student can enroll in a course by typing an enrollment code, then submit a completed run against an assignment; auto-grading evaluates hard gates and scored criteria and stores the result
  3. Student can edit config.mk in both raw Monaco mode and a guided form mode that surfaces editable parameters and enforces locked parameter constraints from the assignment
  4. Student can query layout element details (cell name, net, layer) by clicking on the layout via the click-to-inspect API
  5. Student sees an anonymous leaderboard ranking PPA metrics per assignment; user can compare metrics from multiple runs in a side-by-side view; instructor can view class-wide progress and queue depth
**Plans**: 7 plans

Plans:
- [ ] 02-01-PLAN.md — DB foundation: Alembic migration 0003 (courses, enrollments, assignments, submissions tables + leaderboard indexes), 4 ORM models, all test scaffolds (Wave 0)
- [ ] 02-02-PLAN.md — Course + enrollment backend: POST /courses (enrollment code gen), POST /enroll, assignment CRUD with locked/editable params, instructor role gate
- [ ] 02-03-PLAN.md — Config editor frontend: Form/Raw toggle, Monaco raw mode, guided ParamForm with 7 curated ORFS params, locked-param greying with badge
- [ ] 02-04-PLAN.md — Submission + auto-grading: POST /submit with locked-param validation, checkpoint_eval Celery task, grade push via Redis pubsub + WebSocket, CheckpointCards preview
- [ ] 02-05-PLAN.md — Click-to-inspect: OpenROAD subprocess query endpoint, pixel→micron coordinate mapping with Y-inversion, InspectSidebar sliding panel
- [ ] 02-06-PLAN.md — Leaderboard + run comparison + instructor dashboard: functional B-tree leaderboard query, side-by-side RunComparison with color coding, CSV export, CourseNav sidebar
- [ ] 02-07-PLAN.md — Gap closure: add SQL-level WNS ORDER BY text() expression to get_leaderboard() so idx_runs_wns_numeric B-tree index is used in PostgreSQL; add explicit tiebreaker test

### Phase 3: AI Assistance
**Goal**: Students get plain-language help from a locally-hosted AI that understands their specific run — without sending any design data to cloud services
**Depends on**: Phase 2
**Requirements**: AI-01, AI-02, AI-03
**Success Criteria** (what must be TRUE):
  1. User can request a plain-language explanation of ORFS log errors from a failed stage; the response arrives from local Ollama inference and never sends GDS/DEF or student PII to any cloud service
  2. User can request config parameter suggestions (CLOCK_PERIOD, CORE_UTILIZATION, etc.) based on their current run's PPA metrics; suggestions reference specific values from the run
  3. User can chat with an AI assistant that has context of their current run (log excerpts, PPA metrics, config snapshot) and receive coherent multi-turn answers; Ollama model is warmed on service startup to avoid first-request hang
**Plans**: 3 plans

Plans:
- [ ] 03-01-PLAN.md — AI service foundation: OllamaClient implementation (generate, chat_stream, warm_up with 3-retry), prompt templates (explain_log/timing/drc, advisor_config), OLLAMA_MODEL setting, lifespan warm-up, Wave 0 test infrastructure
- [ ] 03-02-PLAN.md — Log explainer + config advisor: wire explain/advisor endpoints to Ollama, AiExplainPanel (shared), AiAdvisorPanel, aiSlice, integrate into LogTerminal/PpaMetricCards/ConfigEditor
- [ ] 03-03-PLAN.md — Context-aware chat: wire /chat streaming endpoint (NDJSON + X-Accel-Buffering), AiChatTab with context summary + streaming cursor, AI tab in RunDetailPage

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Flow | 9/9 | Complete   | 2026-03-16 |
| 2. Learning Layer | 7/7 | Complete   | 2026-03-15 |
| 3. AI Assistance | 0/3 | Not started | - |
