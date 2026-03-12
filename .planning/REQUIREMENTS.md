# Requirements: ChipAtelier

**Defined:** 2026-03-12
**Core Value:** A student can submit a Verilog design and get a routed layout with metrics — entirely in the browser, on shared university hardware, without installing any tools.

## v1 Requirements

### Authentication

- [ ] **AUTH-01**: User can create an account with email and password
- [ ] **AUTH-02**: User can log in and receive a JWT access token (15min, in response body) and an httpOnly refresh cookie (7 days)
- [ ] **AUTH-03**: User can log out from any page (refresh cookie invalidated)
- [ ] **AUTH-04**: User session persists across browser refresh via automatic access token renewal using the refresh cookie

### Job Lifecycle

- [ ] **JOB-01**: User can create a project and upload Verilog source files and a config.mk
- [ ] **JOB-02**: User can submit a job that runs their design through the full ORFS flow in an isolated Docker container (no network access, cgroup resource limits)
- [ ] **JOB-03**: User sees live log output streaming in a browser terminal (xterm.js) during job execution
- [ ] **JOB-04**: User sees current job status (queued / running / complete / failed / cancelled) and stage-level progress (synthesis → floorplan → place → cts → route → gds)
- [ ] **JOB-05**: User can cancel a running job, which stops the container and marks the job cancelled

### Results & Artifacts

- [ ] **RSLT-01**: User sees PPA metrics (worst negative slack, total negative slack, DRC violation count, core area, total power) after job completes, parsed from ORFS reports
- [ ] **RSLT-02**: User can download completed job artifacts (GDS, DEF, timing reports) via download links backed by MinIO
- [ ] **RSLT-03**: User sees a static layout PNG snapshot within seconds of job completion (fast-path KLayout generation, always present)
- [ ] **RSLT-04**: User can view the full run history for a project, with each run showing status, timestamp, target stage, and key PPA metrics

### Layout Viewer

- [ ] **LAYT-01**: User can launch a VNC viewer tab that opens the OpenROAD Qt GUI with their completed DEF pre-loaded (noVNC → WebSocket proxy via Nginx token routing)
- [ ] **LAYT-02**: User can query layout element details (cell name, instance, net, layer) by providing coordinates via the click-to-inspect API (OpenDB query endpoint on completed DEF)

### Config Editor

- [ ] **EDIT-01**: User can edit a project's config.mk parameters in a guided form mode that surfaces editable parameters with descriptions and enforces locked parameter constraints (when enrolled in an assignment)
- [ ] **EDIT-02**: User can edit config.mk in raw Monaco editor mode when full control is needed (outside assignment constraints)

### Courses & Assignments

- [ ] **COUR-01**: Instructor can create an assignment specifying: design, PDK, target stage, locked parameters, editable parameters, checkpoint rules (hard and scored), and due date
- [ ] **COUR-02**: Instructor can create a course and generate an enrollment code (format: `VLSI-YYYY-XXXX`, 6-8 chars, collision-checked)
- [ ] **COUR-03**: Student can enroll in a course by entering an enrollment code
- [ ] **COUR-04**: Student can submit a completed run against an assignment for grading
- [ ] **COUR-05**: System automatically evaluates checkpoint rules after submission (hard gates: DRC=0, flow complete; scored: WNS/TNS targets with partial credit) and stores the score

### AI Assistance

- [ ] **AI-01**: User can request a plain-language explanation of ORFS log errors from the last N lines of a failed stage (local Ollama inference — design data stays on-premise)
- [ ] **AI-02**: User can request config parameter suggestions (e.g. adjust CLOCK_PERIOD, CORE_UTILIZATION) based on their current run's PPA metrics (local Ollama inference)
- [ ] **AI-03**: User can chat with an AI assistant that has context of their current run (log excerpts, PPA metrics, config snapshot) to ask questions like "why did timing fail?"

### Dashboard & Reporting

- [ ] **DASH-01**: Student can see an anonymous leaderboard for an assignment showing PPA rankings (WNS, area, power) without revealing other students' names
- [ ] **DASH-02**: User can compare metrics across multiple runs for the same project in a side-by-side view
- [ ] **DASH-03**: Instructor can view a class-wide dashboard: per-student run counts, submission status, grade distribution, and current job queue depth
- [ ] **DASH-04**: User sees their current storage usage prominently in the dashboard (e.g., "1.2 GB of 5 GB used")

---

## v2 Requirements

Deferred — not in the current roadmap. Add after v1 is validated in a real classroom.

### Layout Viewer (Tiled)

- **LAYT-V2-01**: User can view the completed layout in an interactive tiled viewer (MapLibre GL, KLayout-generated PNG tiles, per-layer toggling, zoom 0–max_useful_zoom)
- **LAYT-V2-02**: Max useful zoom is computed from design bounding box at tile generation time; not all 0-18 zoom levels are generated

### Authentication (Institutional)

- **AUTH-V2-01**: User can log in via institutional SSO (SAML 2.0 or OIDC)
- **AUTH-V2-02**: Institution admin can configure SSO and domain whitelist

### Infrastructure

- **INFRA-V2-01**: System automatically cleans up run artifacts past their retention period per user storage quota
- **INFRA-V2-02**: Admin panel provides user management, queue monitoring, and manual job control
- **INFRA-V2-03**: Multi-PDK support: GF180 and ASAP7 available alongside SKY130 (no architectural changes required)

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time student-to-student chat | Not core to learning; moderation burden; scope trap |
| In-browser RTL simulation (waveforms) | Different domain; EDAPlayground already covers this |
| Schematic/block diagram editor | ASIC flow starts at RTL; out of domain |
| Collaborative real-time code editing | ASIC design is not a real-time collaborative activity; race conditions on shared config |
| OAuth (Google/GitHub) login | Email/password sufficient for v1; SSO (SAML) covers institutional needs in v2 |
| Auto-submit to MPW shuttle / TinyTapeout | Out of scope; different DRC/LVS requirements; tapeout prep is a separate concern |
| Per-job AI-generated lab writeup | Defeats educational purpose; academic integrity risk |
| Mobile app (iOS/Android) | Layout inspection and VNC unusable on small screens; web-first is correct |
| GDS/DEF sent to cloud LLMs | Privacy violation; Ollama local inference is the constraint |
| Auto-deployment to cloud (AWS/GCP) | Contradicts on-premise, design-data-private model |

---

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 1 | Pending |
| AUTH-02 | Phase 1 | Pending |
| AUTH-03 | Phase 1 | Pending |
| AUTH-04 | Phase 1 | Pending |
| JOB-01 | Phase 1 | Pending |
| JOB-02 | Phase 1 | Pending |
| JOB-03 | Phase 1 | Pending |
| JOB-04 | Phase 1 | Pending |
| JOB-05 | Phase 1 | Pending |
| RSLT-01 | Phase 1 | Pending |
| RSLT-02 | Phase 1 | Pending |
| RSLT-03 | Phase 1 | Pending |
| RSLT-04 | Phase 1 | Pending |
| LAYT-01 | Phase 1 | Pending |
| LAYT-02 | TBD | Pending |
| EDIT-01 | TBD | Pending |
| EDIT-02 | TBD | Pending |
| COUR-01 | TBD | Pending |
| COUR-02 | TBD | Pending |
| COUR-03 | TBD | Pending |
| COUR-04 | TBD | Pending |
| COUR-05 | TBD | Pending |
| AI-01 | TBD | Pending |
| AI-02 | TBD | Pending |
| AI-03 | TBD | Pending |
| DASH-01 | TBD | Pending |
| DASH-02 | TBD | Pending |
| DASH-03 | TBD | Pending |
| DASH-04 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 28 total
- Mapped to phases: 15
- Unmapped (TBD — roadmapper will assign): 13

---
*Requirements defined: 2026-03-12*
*Last updated: 2026-03-12 after initial definition*
