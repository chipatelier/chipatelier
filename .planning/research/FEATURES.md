# Feature Research

**Domain:** Web-based ASIC/EDA education platform (RTL-to-GDS managed environment)
**Researched:** 2026-03-12
**Confidence:** MEDIUM — web search and WebFetch unavailable; findings based on training knowledge
(cutoff August 2025) of Efabless, TinyTapeout, JasperGold Education, Cadence CloudEDA,
academic EDA lab tooling, and the ChipAtelier spec itself. All claims flagged with confidence level.

---

## Competitive Landscape Summary

Before feature categorization, a brief map of what already exists:

| Platform | Model | Key Feature Set | Gap for ChipAtelier |
|----------|-------|-----------------|---------------------|
| **Efabless** | Cloud, shuttle-based | Project hosting, precheck CI, community gallery, MPW shuttle submission | No interactive log streaming, no live stage viewer, no grading/LMS layer, no VNC |
| **TinyTapeout** | GitHub-based CI | Wokwi schematic editor, GHA-driven ORFS flow, per-design tile in group submission, datasheet auto-gen | No managed compute, no live logs, no assignments/grading, no instructor tooling |
| **OpenROAD GUI** | Local desktop Qt app | Full layout inspection, timing analysis, ECO, DRC viewer | Desktop-only; no web, no multi-user, no grading |
| **ORFS Makefile** | CLI/local | Reproducible flow, all stage targets | No UI at all; raw log files |
| **Cadence CloudEDA** | Cloud SaaS (commercial) | Full Virtuoso/Innovus stack in browser | Commercial license; not accessible to students; overkill |
| **Synopsys SolvNetPlus / EDA Playground** | Online IDE | Verilog/SystemVerilog simulation, waveform viewer | Simulation only — no place-and-route, no layout |
| **edaplayground.com** | Free SaaS | RTL sim (Questa, VCS, XCELIUM) | Simulation only; no physical design |
| **JupyterHub + OpenROAD Python API** | Academic (Rice, UCSD) | Notebook-driven ORFS with Python bindings | No web-native UI; notebook paradigm awkward for physical design |

**Conclusion:** No existing open-source platform combines managed RTL-to-GDS compute, live log
streaming, interactive layout viewing, and an LMS-style grading layer. ChipAtelier fills a real gap.
[MEDIUM confidence — based on training data through Aug 2025]

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that users assume exist. Missing any of these makes the product feel broken or unfinished.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Job submission (RTL + config upload)** | Core action — without this, nothing works | MEDIUM | Verilog + SDC + config.mk upload; must validate file types and sizes before queuing |
| **Live log streaming to browser** | Students won't wait blind; they expect Jupyter-style real-time feedback | MEDIUM | WebSocket → xterm.js; Redis pubsub bridge from container stdout already in spec |
| **Job status tracking (queued/running/done/failed)** | Users need to know where their job is in the queue | LOW | Polling or WS push; job state machine already defined |
| **Job cancellation** | Long jobs (routing = 30–90 min) must be stoppable | LOW | Docker stop + Celery revoke; critical for shared compute |
| **Artifact download (GDS, DEF, reports)** | Students need outputs for homework submission, inspection | LOW | MinIO presigned URLs; standard |
| **Layout snapshot after completion** | Students want to see what was built; text-only logs insufficient | MEDIUM | Single PNG from KLayout; must be fast-path (seconds not minutes) |
| **Run history per project** | Users iterate many runs; must be able to go back | LOW | Paginated list with status, timestamp, key metrics |
| **Basic PPA metrics display** | WNS, TNS, DRC count, area — these are the grade; must surface prominently | LOW | Parse ORFS reports; store in JSONB; already in schema |
| **User authentication (login/logout)** | Multi-user system; access control is required | LOW | JWT + httpOnly refresh cookie; email/password for MVP |
| **Project isolation per user** | Shared server; students must not see each other's designs | LOW | Standard; each project scoped to user_id |
| **Resource quota enforcement** | Shared hardware; uncapped jobs will starve other students | MEDIUM | CPU/RAM cgroup limits per container; storage quota per user; already specced |
| **Error reporting (what stage failed, why)** | Raw log dumps are not sufficient; students need actionable failure info | MEDIUM | Stage-level status, last N lines of log at failure point surfaced in UI |
| **Responsive, functional web UI** | This is a web platform; must work in a modern browser without installs | HIGH | React + TypeScript; xterm.js + MapLibre GL; noVNC tab |

### Differentiators (Competitive Advantage)

Features that set ChipAtelier apart. Not universally expected, but high value and not available
in any open-source alternative today.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Interactive tiled layout viewer (MapLibre GL + KLayout tiles)** | Students can pan/zoom/inspect the real layout in the browser at any zoom level; no existing open tool offers this | HIGH | Background Celery task; KLayout Python API; store tiles in MinIO; must keep PNG fast-path while tiles build |
| **VNC viewer tab (noVNC → OpenROAD Qt GUI)** | Full fidelity OpenROAD GUI in browser; click-to-inspect, ECO, timing analysis — exactly what local tool provides, zero install | HIGH | Per-session Docker container; Xvfb + x11vnc + websockify; nginx token proxy; bandwidth-heavy (on-campus only) |
| **Click-to-inspect layout (OpenDB query API)** | Student clicks a cell in the layout viewer and gets net/instance info; teaches design intent vs implementation | HIGH | FastAPI query endpoint; OpenROAD Python API on completed DEF; educationally unique |
| **Assignment system with locked/editable params** | Instructor controls which knobs students can turn; prevents trivial solutions; teaches design space exploration | MEDIUM | JSONB locked_params in assignments table; frontend enforces via form mode config editor |
| **Auto-grading on checkpoint rules** | Objective, instant feedback on DRC=0, WNS targets; replaces TA manual grading of EDA outputs | MEDIUM | Celery checkpoint_eval task; configurable JSONB rules per assignment |
| **Anonymous leaderboard per assignment** | Gamification; students see their ranking on WNS/area/power without revealing names; motivates iteration | LOW | Aggregate query over submissions; anonymous display |
| **Run comparison view (side-by-side metrics)** | Students learn by seeing what changed between runs; unique to managed platform | MEDIUM | Diff view across runs; plot PPA trend over iterations |
| **AI log explainer (Ollama, on-premise)** | Converts cryptic ORFS error messages into human-readable explanations; dramatically reduces TA office hours | HIGH | Local Ollama inference; design data never leaves server; prompts per error type |
| **AI config advisor** | Suggests parameter changes (CLOCK_PERIOD, CORE_UTILIZATION) based on current run metrics; guided learning | HIGH | Context injection with current metrics + config; requires AI service |
| **Context-aware AI chat** | Student can ask "why did timing fail?" and get an answer grounded in their actual run data | HIGH | RAG-lite: inject log excerpts + metrics into prompt; session-scoped |
| **Config editor dual-mode (Monaco raw + guided form)** | Form mode exposes only editable params with sliders/dropdowns + tooltips; Monaco for advanced users | MEDIUM | Monaco editor + React form; locked params grayed out; teaches what each param does |
| **One-command Docker Compose deploy** | Any university IT staff can deploy without EDA expertise; no cloud vendor; no per-seat license | MEDIUM | docker-compose.yml + .env.example + install.sh; already planned but needs careful UX polish |
| **Community assignment library** | Instructors share labs; avoids duplicating effort across universities; builds ecosystem | LOW | assignments/ YAML format in repo; students don't see this layer, but instructors do |
| **Stage-level progress visualization** | Flow control panel shows synthesis → floorplan → place → cts → route → gds as a stepper; student understands the flow | LOW | Parse stage transition events from log; already in architecture |
| **Storage usage visible to students** | "1.2 GB of 5 GB used" in dashboard; students self-manage, reducing IT tickets and confusing failures | LOW | Aggregate storage_bytes from runs; display prominently |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create more problems than they solve for ChipAtelier's scope.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Real-time student-to-student chat** | Students want to collaborate / ask peers | Not core to learning; adds moderation burden; pushes scope into social platform territory | Point students to existing channels (Discord, Slack, Piazza) |
| **In-browser RTL simulation (waveform viewer)** | Students want a full toolchain in the browser | Doubles scope; simulation and physical design are separate problem domains; EDAPlayground already does sim | Link to EDAPlayground or recommend local iverilog/verilator; out of scope |
| **Schematic / block diagram editor** | Non-RTL users want a visual entry point | ASIC flow starts at RTL; schematic capture is a different workflow; would require separate toolchain | Provide starter Verilog templates in assignment library |
| **Collaborative real-time code editing (Google Docs style)** | Seems modern and useful | ASIC design is not a real-time collaborative activity; race conditions on shared config/source harmful | Git-based version history (source_versions table) is sufficient |
| **Auto-deployment to cloud (AWS/GCP)** | Admins want elastic scale | Contradicts the on-premise, design-data-private model; adds operational complexity and cost; multi-cloud is a different product | Docker Compose is the target; Kubernetes Helm chart as optional extension |
| **Full commercial EDA workflow (Innovus, Virtuoso, DC)** | Advanced users want more tools | Commercial license issues; not reproducible; defeats open-source mission | Stick to OpenROAD + open PDKs; document upgrade path for institutions with licenses |
| **Student-facing CI/CD pipeline (GitHub Actions integration)** | Devs want to trigger jobs from git push | Adds OAuth surface, webhook complexity, security exposure; ChipAtelier is a portal, not a CI system | Students submit from the UI; version history captured in source_versions |
| **Mobile app (iOS/Android)** | Users want native apps | Physical design layout inspection on a 6" screen is not useful; VNC is unusable on mobile | Web-first; responsive design for dashboard; heavy features (VNC, layout) are desktop-only by nature |
| **Real-time multi-user layout annotation** | Teachers want to point to things live | Complex CRDT / signaling layer; niche use case | VNC tab already shows the layout; instructor can screen-share via meeting tool |
| **Containerized per-student persistent VM** | Students want a persistent shell environment | Expensive compute; not needed since ORFS job lifecycle handles environment; opens persistent attack surface | Jobs are ephemeral by design; artifact storage in MinIO persists what matters |
| **Per-job AI-generated full lab writeup** | Save students time writing reports | Defeats the educational purpose; instructors will see this as academic dishonesty risk | AI explains errors and suggests fixes, but student writes the analysis |
| **Auto-submit to MPW shuttle / TinyTapeout** | End-to-end to silicon | Out of scope; different DRC/LVS requirements; tapeout prep is a different course | Document export path; let students take GDS and submit separately |

---

## Feature Dependencies

```
[User Auth]
    └──required by──> [Job Submission]
    └──required by──> [Project Management]
    └──required by──> [Assignment Enrollment]
    └──required by──> [VNC Session]

[Job Submission]
    └──required by──> [Live Log Streaming]
    └──required by──> [Layout Snapshot]
    └──required by──> [Artifact Download]
    └──required by──> [PPA Metrics Display]
    └──required by──> [Run History]
    └──required by──> [VNC Viewer Tab]

[Layout Snapshot (PNG)]
    └──required before──> [Tiled Layout Viewer]
    └──fast-path preserved when──> [Tiled Layout Viewer]

[Tiled Layout Viewer]
    └──enhances──> [Click-to-Inspect (OpenDB Query)]

[Run History]
    └──required by──> [Run Comparison View]

[Assignment System]
    └──required by──> [Auto-Grading]
    └──required by──> [Anonymous Leaderboard]
    └──required by──> [Config Editor Locked Params]

[Auto-Grading]
    └──required by──> [Anonymous Leaderboard]
    └──feeds──> [Instructor Dashboard]

[PPA Metrics Display]
    └──required by──> [AI Config Advisor]

[Live Log Streaming]
    └──required by──> [AI Log Explainer]
    └──feeds──> [Stage-Level Progress Visualization]

[AI Log Explainer + AI Config Advisor]
    └──required by──> [AI Context-Aware Chat]

[Docker Compose Deploy]
    └──enables──> [One-Command University Deploy]
```

### Dependency Notes

- **Layout Snapshot must precede Tiled Layout Viewer:** The PNG fast-path (seconds) must stay
  permanent even after tiles are available. Tiles take 2–5 minutes as a background task; without
  the PNG, the layout area is blank during tile generation — bad UX.
- **Assignment System is the gate for grading features:** Leaderboard, auto-grading, locked params,
  and instructor dashboard all depend on the Assignment model existing. These are a Phase 2 block.
- **AI features require a working job pipeline first:** AI log explainer needs real logs from real
  jobs. Building AI before the core job pipeline is backwards.
- **Click-to-inspect requires tiled viewer as context:** The click coordinates are meaningful only
  when the user is looking at the tiled layout; layering query on the PNG-only view is insufficient.
- **Stage-level progress is a display enhancement** on the log streaming infrastructure; it requires
  log streaming to be working but does not add a new backend service.

---

## MVP Definition

### Launch With (v1 — Phase 1)

Minimum viable product: a student can submit a design and see what happened.

- [x] User auth (email/password, local accounts)
- [x] Project creation + Verilog/config.mk upload
- [x] Job submission → ORFS container → execution
- [x] Live log streaming (WebSocket → xterm.js)
- [x] Job status tracking and cancellation
- [x] Static layout snapshot (single KLayout PNG, seconds not minutes)
- [x] PPA metrics display (WNS, TNS, DRC count, area, power)
- [x] Artifact download (GDS, DEF, timing reports)
- [x] Run history per project
- [x] VNC viewer tab (noVNC → OpenROAD Qt GUI, pre-loaded DEF)
- [x] Storage quota display ("1.2 GB of 5 GB used")
- [x] Stage-level progress stepper (derived from log streaming)

### Add After Validation (v1.x — Phase 2)

Add once the core flow is proven reliable in a real classroom:

- [ ] Tiled layout viewer (MapLibre GL + KLayout tiles) — add when PNG snapshot proves insufficient
- [ ] Click-to-inspect (OpenDB query API) — enhances tiled viewer; pair together
- [ ] Assignment system (create, enroll, submit) — needed for formal course use
- [ ] Auto-grading (checkpoint rules) — needed for assignments
- [ ] Anonymous leaderboard — motivational; add with auto-grading
- [ ] Config editor form mode (guided, locked/editable params) — add with assignment system
- [ ] Run comparison view — add once students have multiple runs to compare
- [ ] Instructor dashboard — add with assignment system

### Future Consideration (v2+ — Phase 3)

Defer until the platform has real classroom usage and feedback:

- [ ] AI log explainer — high value but depends on prompt quality; tune on real student errors
- [ ] AI config advisor — similar; needs real run data to validate recommendations
- [ ] AI context-aware chat — most complex; requires validated explainer and advisor first
- [ ] SSO (SAML 2.0 + OIDC) — needed for institutional adoption at scale; not day-one
- [ ] Multi-PDK (GF180, ASAP7) — no architectural changes; add when SKY130 is stable
- [ ] Community assignment library (published) — needs assignments from real instructors first
- [ ] Storage retention automation — needed at scale; manual cleanup sufficient initially
- [ ] Admin panel — needed at scale; direct DB + Docker management sufficient for early adopters

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Job submission + ORFS execution | HIGH | MEDIUM | P1 |
| Live log streaming | HIGH | MEDIUM | P1 |
| Layout snapshot (PNG) | HIGH | LOW | P1 |
| Job status + cancellation | HIGH | LOW | P1 |
| PPA metrics display | HIGH | LOW | P1 |
| Artifact download | HIGH | LOW | P1 |
| User auth + project isolation | HIGH | LOW | P1 |
| VNC viewer tab | HIGH | HIGH | P1 |
| Stage-level progress stepper | MEDIUM | LOW | P1 |
| Storage usage display | MEDIUM | LOW | P1 |
| Tiled layout viewer | HIGH | HIGH | P2 |
| Click-to-inspect (OpenDB) | HIGH | HIGH | P2 |
| Assignment system + auto-grading | HIGH | MEDIUM | P2 |
| Anonymous leaderboard | MEDIUM | LOW | P2 |
| Config editor form mode | MEDIUM | MEDIUM | P2 |
| Run comparison view | MEDIUM | MEDIUM | P2 |
| Instructor dashboard | MEDIUM | MEDIUM | P2 |
| AI log explainer | HIGH | HIGH | P3 |
| AI config advisor | HIGH | HIGH | P3 |
| AI context-aware chat | MEDIUM | HIGH | P3 |
| SSO (SAML/OIDC) | MEDIUM | MEDIUM | P3 |
| Multi-PDK support | MEDIUM | LOW | P3 |
| Admin panel | LOW | MEDIUM | P3 |
| Storage retention automation | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch (Phase 1)
- P2: Should have, add when core is validated (Phase 2)
- P3: Nice to have, future consideration (Phase 3)

---

## Competitor Feature Analysis

| Feature | Efabless | TinyTapeout | EDA Playground | ChipAtelier Plan |
|---------|----------|-------------|----------------|-----------------|
| Managed RTL-to-GDS compute | YES (cloud) | YES (GitHub Actions) | NO (sim only) | YES (on-premise Docker) |
| Live log streaming | NO | NO (GHA logs only) | NO | YES (WebSocket xterm.js) |
| Interactive layout viewer | NO | Basic GDS preview | NO | YES (MapLibre GL tiles + VNC) |
| Assignment / grading system | NO | NO | NO | YES (Phase 2) |
| AI assistance | NO | NO | NO | YES (Phase 3, local Ollama) |
| VNC / remote GUI | NO | NO | NO | YES (noVNC tab) |
| Click-to-inspect layout | NO | NO | NO | YES (Phase 2, OpenDB API) |
| Anonymous leaderboard | NO | NO | NO | YES (Phase 2) |
| Self-hostable, open source | NO (proprietary) | Partial (GHA) | NO | YES (Apache 2.0 Docker Compose) |
| Multi-user, multi-course | NO | NO | NO | YES |
| Queue management | Basic | GHA queue | N/A | YES (Celery + instructor view) |
| Design data privacy (on-prem) | NO (cloud) | NO (cloud CI) | NO | YES (Ollama, no cloud LLM) |

**Sources (confidence level):**

- Efabless platform features: MEDIUM confidence (training data, platform publicly documented through mid-2025)
- TinyTapeout workflow: MEDIUM confidence (GitHub repo and docs publicly available through mid-2025)
- EDA Playground: HIGH confidence (stable, well-documented, simulation-only platform)
- JupyterHub + OpenROAD academic use: MEDIUM confidence (Rice University, UCSD publicly documented work)
- OpenROAD GUI capabilities: HIGH confidence (open source, well-documented)
- ChipAtelier spec analysis: HIGH confidence (primary source — CLAUDE.md and PROJECT.md)

---

## Sources

- ChipAtelier CLAUDE.md — primary spec source (HIGH confidence)
- ChipAtelier PROJECT.md — requirements and constraints (HIGH confidence)
- Efabless platform documentation (training data, cutoff Aug 2025) — MEDIUM confidence
- TinyTapeout GitHub repository and documentation (training data, cutoff Aug 2025) — MEDIUM confidence
- OpenROAD open source repository and documentation (training data, cutoff Aug 2025) — HIGH confidence
- EDA Playground (edaplayground.com) feature set — HIGH confidence (stable, unchanged)
- Academic EDA teaching patterns (Rice, UCSD, Purdue documented course tooling) — MEDIUM confidence
- NOTE: WebSearch and WebFetch were unavailable during this research session. All competitor
  claims should be spot-checked against current platform pages before finalizing roadmap decisions.

---
*Feature research for: Web-based ASIC/EDA education platform (ChipAtelier)*
*Researched: 2026-03-12*
