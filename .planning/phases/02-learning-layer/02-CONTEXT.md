# Phase 2: Learning Layer - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Course and assignment platform on top of the Phase 1 pipeline. Instructors create courses with human-readable enrollment codes, define assignments with locked/editable ORFS parameters and checkpoint rules, and manage class-wide progress. Students enroll via code, run jobs through the existing pipeline, submit completed runs for auto-grading, view checkpoint scores, and compare runs on an anonymous leaderboard. Also includes the guided config editor (form mode for ORFS parameters), click-to-inspect layout element query, run comparison view, and instructor dashboard. AI assistance, SSO, and admin panel are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Assignment creation interface
- Form wizard, not YAML upload — step-by-step: design + PDK → locked/editable param picker → checkpoint rule builder → due date
- Locked/editable params selected via checkbox list showing the curated safe subset from CLAUDE.md (CORE_UTILIZATION, PLACE_DENSITY, TNS_END_PERCENT, CLOCK_PERIOD, CORE_ASPECT_RATIO, CORE_MARGIN, SETUP_SLACK_MARGIN)
- Checkpoint rules authored via rule builder UI: pick metric from dropdown → pick operator (≥, =, ≤) → enter value → pick 'hard gate' or 'scored'. No JSON authoring required.
- Locked params require setting the forced value in the form (e.g. CLOCK_PERIOD=10). Passed as Make CLI args at job invocation — highest priority, overrides student config.mk.
- 1 assignment per course. Instructors clone/copy for reuse across sections.
- Assignment visibility: hidden until instructor explicitly opens it (not auto-released on enrollment)
- Multiple submissions allowed up to due date; system keeps the highest score

### Config editor form mode
- Guided form mode: each editable param gets label + description + number input + valid range indicator (e.g. "CORE_UTILIZATION: 20–80")
- Locked params visible in form mode with their forced value and a "Locked by instructor" badge — shown greyed out, not hidden
- Mode switch: Form / Raw toggle in the Config tab header (not separate tabs, not hidden behind a link)
- Form mode available even without assignment enrollment — shows all curated params with no locked params in that context

### Grading feedback UX
- On submission: optimistic "Submitted — grading in progress..." banner on the run; Celery task runs async; results pushed via existing WebSocket when complete
- Grade breakdown: inline checkpoint cards — each shows metric name, target, actual value, pass/fail, and points earned. Hard gates show ✓/✗. Scored criteria show "WNS: 40/40 pts" or "20/40 pts (partial credit)".
- Score location: shown in the Assignments panel only (not on the run history table). Run history table shows "Submitted" status.
- Live checkpoint preview in Results tab BEFORE submission: shows how the run would score against the active assignment's checkpoint rules. Student sees "DRC: 0 ✓", "WNS: -0.3 ✗ (need ≥ -0.1)" before clicking Submit. Encourages self-correction.

### Leaderboard + run comparison
- Anonymity: student sees their own name highlighted in their row; all other students shown as rank number only (no names, no handles)
- Sort: primary = total checkpoint score; tiebreaker = WNS
- Leaderboard lives inside each assignment: assignment detail view has tabs — Instructions | Submit | Leaderboard
- Run comparison: side-by-side metrics table — runs as columns, metrics as rows. Highlights better/worse values with color (green/yellow/red). Student checks 2-4 runs from their run history. Metrics shown: WNS, TNS, DRC violations, core utilization, total power, CLOCK_PERIOD (and other config.mk params that vary across selected runs).

### Click-to-inspect layout
- Student clicks directly on the layout PNG image; click coordinates sent to the click-to-inspect API
- Results displayed in a right-side sidebar panel that slides in alongside the layout — persists until dismissed
- Info shown per element: cell instance name, cell type/master, net name(s), layer
- On miss (empty space): "No element at this location" message in the sidebar panel
- Existing LayoutSnapshot component extended to handle click events and coordinate mapping

### Course enrollment and navigation
- New "Courses" section in main sidebar nav after enrollment (separate from personal Projects section)
- Inside course: Assignments list. Each assignment has tabs: Instructions | Submit | Leaderboard
- Submission flow: student opens assignment → clicks "Submit a Run" → modal picker shows eligible completed runs from their projects
- No assignment-dedicated project auto-created on enrollment; student submits any completed run from any personal project
- Locked param enforcement at submission validation time: backend checks run's config.mk has locked param values matching the assignment. Rejected with clear error if mismatch (e.g. "CLOCK_PERIOD must be 10 — your run used 8").

### Instructor dashboard
- Primary view: per-student progress table (rows = students; columns: name, run count, last run status, submission status, score). Sortable.
- Actions: view only + CSV export of scores. No manual grade override in Phase 2.
- Queue info: queue depth (jobs waiting) + running jobs count + recent failures. Simple operational view.
- Dashboard lives inside course page as a "Dashboard" tab (alongside "Assignments" and "Students" tabs)

### Claude's Discretion
- Empty state design for Courses section before enrollment
- Exact visual styling for the checkpoint preview cards in Results tab
- Instructor assignment list / course page layout details
- Error state handling for submission validation failures
- CSV export format details
- Click-to-inspect coordinate scaling between rendered PNG size and design micron coordinates

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `LayoutSnapshot/` component: existing PNG viewer — extend to handle click events and map pixel → micron coordinates for click-to-inspect
- `StageStatusBar/` component: stage progress bar — reusable in assignment context view
- `RunHistoryTable/` component: run list table — reusable for the assignment submission run picker modal
- `PpaMetricCards/` component: PPA metric cards in Results tab — extend for checkpoint preview cards
- `useLogStream.ts` hook: WebSocket subscription pattern — reuse same pattern for WebSocket grade push notification
- `jobSlice.ts` / `authSlice.ts` in Zustand store: established store pattern — add `courseSlice.ts`, `assignmentSlice.ts`
- `backend/app/api/routes/`: existing route file per entity — add `courses.py`, `assignments.py`, `submissions.py`
- `backend/app/models/submission.py`: submission model already scaffolded from Phase 1 plan 01-07
- `backend/app/services/metrics_service.py`: PPA metric parsing — reuse for checkpoint evaluation metric lookup
- `ai.py` route: already in routes (scaffolded but empty) — Phase 3

### Established Patterns
- Zustand slices for entity state (auth, job, project) → add course/assignment slices following same pattern
- FastAPI route files per entity with `Depends(get_current_user)` auth gate → follow same for courses/assignments
- Celery background worker (`background-worker`) already dedicated for checkpoint evaluation, tile generation, AI hints — checkpoint evaluation Celery task goes here
- JSONB `ppa` + `config` columns with functional B-tree indexes on `(ppa->>'worst_negative_slack')` and `(config->>'CLOCK_PERIOD')` — leaderboard ordering uses these directly
- `checkpoint_rules` JSONB on `assignments` table already in DB schema — already defined in CLAUDE.md
- WebSocket push via Redis pubsub already established for log streaming — reuse same pattern for grade push notification

### Integration Points
- Assignment locked params → Make CLI args injected by `orfs_job.py` Celery task at job invocation (existing injection point in worker)
- Checkpoint evaluation Celery task runs after `orfs_job.py` completes (chain via `link=` or explicit dispatch in job completion handler)
- Click-to-inspect API (`/api/v1/query/{runId}`) → already in CLAUDE.md API design, needs implementation in Phase 2
- Leaderboard ordering uses existing GIN + functional B-tree indexes on `runs.ppa` — `ORDER BY (ppa->>'worst_negative_slack')::numeric` already indexed
- Enrollment code generation (VLSI-YYYY-XXXX format) is a decided pattern from CLAUDE.md — implement in `courses.py`

</code_context>

<specifics>
## Specific Ideas

- Run comparison column selection: student checks 2-4 runs from their history (checkboxes in RunHistoryTable) → side-by-side view opens. Config params that differ between selected runs should be shown in the comparison (not just PPA metrics) — this is how students understand what they changed.
- Checkpoint preview in Results tab: reuse the same checkpoint evaluation logic server-side as a "dry run" endpoint (or compute client-side from run's ppa + assignment checkpoint rules fetched on mount). Don't evaluate an actual submission — just show a live preview.
- Assignment visibility toggle: instructor "opens" an assignment from the assignment detail page (not from a separate settings screen). Simple toggle: "Open to students / Close".

</specifics>

<deferred>
## Deferred Ideas

- ORFS canary CI hardening (pin + canary workflow) — noted in CLAUDE.md as Phase 2 work; not part of the Learning Layer plan per se, fits in infra/ops work within Phase 2 or as a quick task
- GF180 / ASAP7 PDK support — Phase 3 or post-v1 (no architectural changes required per CLAUDE.md)
- Manual grade override by instructor — noted as Phase 2 stretch; deferred to post-v1 or a separate quick task
- KLayout tiled interactive viewer (MapLibre GL) — listed as v2 requirement in REQUIREMENTS.md; not in Phase 2 scope as scoped in ROADMAP.md
- VNC "suspended" state (container pause/resume) — Phase 2 deferred idea from Phase 1 context; not in scope here
- Three-tier design library (instructor-provided + community tiers) — Phase 2 deferred idea from Phase 1 context; not in scope here

</deferred>

---

*Phase: 02-learning-layer*
*Context gathered: 2026-03-15*
