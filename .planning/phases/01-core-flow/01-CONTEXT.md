# Phase 1: Core Flow - Context

**Gathered:** 2026-03-13
**Updated:** 2026-03-14 (CLAUDE.md spec corrections: ORFS invocation, ODB/VNC, WebP layout, metrics schema)
**Status:** Ready for planning

<domain>
## Phase Boundary

Full RTL-to-GDS pipeline in the browser: user authentication, project creation with Verilog file upload, job submission running in an isolated ORFS Docker container, live log streaming via WebSocket to xterm.js, artifact storage in MinIO, ORFS auto-generated WebP layout overview images (no KLayout in Phase 1), artifact downloads, VNC viewer integration pre-loaded with a user-selected stage ODB via open.tcl, and storage usage display. Assignments, tiled viewer, AI assistance, and leaderboard are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Main portal layout
- After login, user lands on a project list/grid (card per project showing project name + run count)
- "New Project" button prominent in the header
- Run detail screen uses tabbed layout: Logs | Results | Config
- Flow stage progress (Synth → Floorplan → Place → CTS → Route → GDS) is always visible in a persistent status bar above the tabs — user never has to switch tabs to check stage progress
- Navigation uses breadcrumb: Projects → [project name] → run #N
- Project page shows a run list table (status, timestamp, target stage, key PPA metrics); click to open run detail
- Run/Cancel button lives in the header area alongside stage status bar

### Log terminal experience
- Auto-scroll on by default; pauses automatically if user scrolls up to review; "Jump to bottom" button appears when paused; auto-scroll resumes when user scrolls back to bottom
- Stage transitions injected as separator lines in the terminal output (e.g. `═══ FLOORPLAN ══════════════════════`) in a distinct style — makes it easy to scan and find where each stage starts
- Unlimited scrollback in the browser (no xterm.js scrollback cap)
- When a new run starts, navigate to the new run's detail page with a fresh terminal; prior run's logs preserved and accessible via the project's run list

### Results & metrics display
- PPA metrics shown as cards in the Results tab: WNS, TNS, DRC violation count, core area, total power — each with label + value + color indicator (green/yellow/red based on thresholds)
- Layout overview: gallery/tab strip showing all 6 ORFS auto-generated WebP images (final_all | Routing | Placement | Clocks | IR Drop | Congestion); default view is final_all
- For partial runs (target stage is not finish): empty state placeholder in layout section — "Layout images are generated at the finish stage. Run to GDS to see layout."
- **No KLayout in Phase 1** — ORFS auto-generates WebP images in `reports/{platform}/{design}/base/`; worker copies these to MinIO and serves them directly
- "Open in VNC viewer" button in Results tab; launches inline stage picker modal before opening VNC tab
- Results tab is disabled/greyed out while job is running; automatically activates and switches to it when job completes
- Download links for GDS, DEF, and timing reports also in the Results tab

### VNC viewer integration
- User-selected stage: inline stage picker modal appears when user clicks "Open in VNC viewer" — lists all stages with a completed .odb file (floorplan, place, cts, route, finish), grayed out if not complete
- Worker sets `DESIGN_CONFIG` and `ODB_FILE` env vars; `open.tcl` infers SDC from `DESIGN_CONFIG` — no explicit SDC path needed
- STAGE_ODB mapping: `{"floorplan": "2_floorplan.odb", "place": "3_place.odb", "cts": "4_cts.odb", "route": "5_route.odb", "finish": "6_final.odb"}`
- VNC container launches: `Xvfb :99`, `x11vnc`, `websockify`, then `$OPENROAD_EXE -gui /OpenROAD-flow-scripts/flow/scripts/open.tcl`

### File upload & re-run flow
- Multi-file Verilog upload: students can upload multiple .v/.sv files; one is designated as the top module
- "New Run" forks config.mk from the last run of the project by default; student tweaks parameters and submits; source files reused unless explicitly replaced — fast iteration loop
- Only one active run per project at a time; the "New Run" button is disabled while a run is running; student must cancel the active run before starting a new one (no queuing confusion)

### ORFS invocation
- Make-based: `docker run ... openroad/orfs bash -c "cd /workspace && make --file=/OpenROAD-flow-scripts/flow/Makefile DESIGN_CONFIG=/workspace/config.mk [TARGET]"`
- Instructor-locked parameters passed as Make command-line args (highest priority, overrides config.mk): e.g. `make CLOCK_PERIOD=10 PLATFORM=sky130hd ...`
- Worker parses `PLATFORM` and `DESIGN_NAME` from config.mk at job submission time — stores on run record so artifact paths are deterministic without filesystem scanning after container exits
- Full config snapshot (config.mk contents + locked overrides applied) stored in `runs.config` JSONB for audit trail and Phase 2 run comparison

### Workspace and artifact paths
- Workspace mounted at `/workspace` inside the ORFS container; PDKs at `/pdks` (read-only)
- Results: `/workspace/results/{PLATFORM}/{DESIGN_NAME}/base/` — ODB files, GDS, DEF
- Logs: `/workspace/logs/{PLATFORM}/{DESIGN_NAME}/base/` — per-stage JSON metrics + text logs
- Reports: `/workspace/reports/{PLATFORM}/{DESIGN_NAME}/base/` — auto-generated WebP overview images
- Worker resolves paths as: `results/{platform}/{design}/base/{stage}.odb` using platform+design parsed from config.mk

### Metrics schema
- Per-stage JSON files use `{stage}__{category}__{metric}` key format (e.g. `floorplan__timing__setup__ws`)
- Worker merges all per-stage JSONs into a unified dict after job completion
- Two JSONB columns in `runs` table:
  - `ppa` — friendly-mapped summary: WNS, TNS, DRC, core_utilization, total_power, die_area (via METRIC_MAP lambdas)
  - `stage_metrics` — full raw merged dict keyed by stage prefix for deep queries
- `config` — separate JSONB column storing config.mk snapshot + locked overrides
- METRIC_MAP prefers `finish__*` stage values, falls back to `route__*` when finish stage not run
- Phase 1 indexes: GIN index on `ppa`, functional B-tree on `(ppa->>'worst_negative_slack')` and `(config->>'CLOCK_PERIOD')`

### v2 Spec Amendments (gaps for 01-07-PLAN)

#### Database — pgvector
- Include `pgvector` extension in the PostgreSQL Docker image from day one
- Add `CREATE EXTENSION IF NOT EXISTS vector;` in the initial migration
- No vector columns needed in Phase 1 — just ensures zero-pain migration when Phase 3 AI adds vector search

#### Job queue architecture
- Three queues: `high_priority`, `normal`, `background`
- High-priority drains before normal: instructor reference runs + admin/canary CI runs only
- Normal queue: all student flow jobs, **round-robin per student** using Redis sorted sets — one student with many queued runs cannot starve other students
- Background queue: dedicated worker (1–2 concurrency), tile generation, checkpoint evaluation, AI hints

#### Container warm pool
- Pool of pre-started ORFS containers in ready state, size = `MAX_CONCURRENT_JOBS / 2`
- A replacement container starts immediately when one is claimed from the pool
- Target start latency: <1 second (vs 5–10s cold start)
- Implemented in `worker/container/warm_pool.py`

#### Failure handling and auto-retry
- **Tool crash** (ORFS segfault, OOM kill): auto-retry once after 30 seconds, then mark failed
- **Design error** (bad Verilog/SDC): no retry — show error + AI explanation
- **Timeout**: kill container, notify student, no retry
- **Worker crash**: Redis automatically requeues — new worker picks up

#### Run notes
- Each run has a `notes` text field (plain text, nullable)
- **Private by default** — notes are only visible to the student
- Notes become visible to the instructor only when the student explicitly submits that run for assignment grading
- UI: small editable text area in the Results tab (or below the run list entry)

#### AI service colocation (MVP)
- AI routes live inside `backend/app/ai/` — no separate `ai-service` container in MVP
- Ollama continues as its own container in Docker Compose (separate process, GPU-mappable)
- `ai-service/` directory in repo is scaffolded but not wired into docker-compose.yml until Phase 3
- This simplifies Docker Compose for single-server MVP deployments

### Claude's Discretion
- Empty state design for project list (first-time user, no projects yet)
- Exact loading skeleton / spinner designs
- Config tab content in Phase 1 (raw config.mk view; guided form mode is Phase 2)
- Error state handling for failed jobs in terminal vs. results tab
- Storage usage display placement within the UI (DASH-04 requirement: show "X GB of Y GB used")

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — fresh project, no existing code

### Established Patterns
- None yet — this phase establishes the patterns

### Integration Points
- This phase lays all foundational patterns: FastAPI routes, SQLAlchemy models, Celery task structure, React component architecture, Zustand store shape, xterm.js integration, WebSocket hook pattern
- Phase 2 components (config editor, click-to-inspect, leaderboard) will connect to project/run models and API routes established here

</code_context>

<specifics>
## Specific Ideas

- Stage status bar mockup: `Synth✓  Floor✓  Place↻  CTS-  Route-` — compact, always visible above tabs, conveys completed/running/pending at a glance
- Run detail tabs: Logs (active during run), Results (active after completion, disabled during run), Config (always accessible)
- The fork-from-previous-run model means the typical student workflow is: open project → New Run → tweak CLOCK_PERIOD → Submit → watch logs → see results → repeat
- VNC stage picker: small modal before tab opens, lists completed stages as selectable options with stage name + ODB filename shown

</specifics>

<deferred>
## Deferred Ideas

- GeoJSON vector overlays (congestion heatmap, DRC violation markers, timing critical path polyline) → Phase 2 layout viewer
- Stage-specific default views (floorplan/placement/CTS/routing/finish) → Phase 2 layout viewer
- VNC `suspended` state (container pause/resume within 1 hour) → Phase 2 VNC lifecycle
- Design space exploration / parameter sweep mode → Phase 2 or Phase 3
- Three-tier design library (instructor-provided + community tiers) → Phase 2
- KLayout tile pyramid for interactive zoom viewer → Phase 2

</deferred>

---

*Phase: 01-core-flow*
*Context gathered: 2026-03-13*
*Context updated: 2026-03-14*
