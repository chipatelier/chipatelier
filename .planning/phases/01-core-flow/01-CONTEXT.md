# Phase 1: Core Flow - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Full RTL-to-GDS pipeline in the browser: user authentication, project creation with Verilog file upload, job submission running in an isolated ORFS Docker container, live log streaming via WebSocket to xterm.js, artifact storage in MinIO, static layout PNG snapshot, artifact downloads, VNC viewer integration pre-loaded with the completed DEF, and storage usage display. Assignments, tiled viewer, AI assistance, and leaderboard are separate phases.

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
- Static layout PNG displayed in the Results tab, below the metric cards, large enough to see the design shape
- "Open in VNC viewer" button directly below the layout PNG
- Results tab is disabled/greyed out while job is running; automatically activates and switches to it when job completes
- Download links for GDS, DEF, and timing reports also in the Results tab

### File upload & re-run flow
- Multi-file Verilog upload: students can upload multiple .v/.sv files; one is designated as the top module
- "New Run" forks config.mk from the last run of the project by default; student tweaks parameters and submits; source files reused unless explicitly replaced — fast iteration loop
- Only one active run per project at a time; the "New Run" button is disabled while a run is running; student must cancel the active run before starting a new one (no queuing confusion)

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

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-core-flow*
*Context gathered: 2026-03-13*
