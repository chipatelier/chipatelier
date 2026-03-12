# ChipAtelier

## What This Is

ChipAtelier is an open-source, web-based ASIC learning platform that gives university students
a fully managed RTL-to-GDS implementation environment using the OpenROAD toolchain (ORFS).
Students log in through a browser, submit design jobs, stream live logs, inspect layouts, and
receive AI-assisted feedback — no local EDA tool installation required. Any university can
self-host it on a single on-premise server via Docker Compose.

## Core Value

A student can submit a Verilog design and get a routed layout with metrics — entirely in the browser,
on shared university hardware, without touching a terminal or installing any tools.

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Phase 1 — Core Flow:**
- [ ] Docker Compose stack brings up all services (frontend, backend, worker, postgres, redis, minio)
- [ ] User can create an account and log in (local email/password, JWT + httpOnly refresh cookie)
- [ ] User can create a project and upload Verilog + config.mk
- [ ] User can submit a job that runs in an isolated ORFS Docker container
- [ ] User sees live log streaming in the browser terminal (WebSocket → xterm.js)
- [ ] Job completes and artifacts (reports, GDS, DEF) are stored in MinIO
- [ ] User sees a static layout snapshot (single PNG from KLayout) after job completes
- [ ] User can launch a VNC viewer tab pre-loaded with their DEF (noVNC → OpenROAD Qt GUI)
- [ ] User can cancel a running job

**Phase 2 — Learning Layer:**
- [ ] Tiled layout viewer (MapLibre GL compositing KLayout-generated tiles)
- [ ] Instructor can create assignments with locked/editable params and checkpoint rules
- [ ] Student can enroll in a course via enrollment code and submit a run for grading
- [ ] Auto-grading evaluates checkpoint rules (DRC=0, WNS targets) and stores score
- [ ] Anonymous leaderboard shows PPA rankings per assignment
- [ ] Config editor with form mode (Monaco for raw, form for guided)
- [ ] Run comparison view (side-by-side metrics across runs)
- [ ] Instructor dashboard (class progress, queue status)

**Phase 3 — AI + Polish:**
- [ ] AI log explainer (Ollama, local inference — design data stays on-premise)
- [ ] AI config advisor suggests parameter changes
- [ ] AI context-aware chat for student assistance
- [ ] SSO (SAML 2.0 + OIDC) for institutional login
- [ ] Storage quota enforcement and automated retention cleanup
- [ ] Admin panel (queue management, user management)

### Out of Scope

- Real-time chat between students — not core to the learning value
- Mobile app — web-first, browser is sufficient
- OAuth (Google/GitHub) login — email/password sufficient for v1; SSO via SAML in Phase 3
- Video posts / media uploads — not relevant to ASIC learning
- Multi-cloud managed deployment — Docker Compose on single server is the target
- GF180 / ASAP7 PDKs — deferred to Phase 2; no architectural changes needed when added

## Context

- **Target hardware:** Single on-premise server (HP DL380 Gen9, dual E5-2600 ~28-36 cores)
  — at 4-8 cores/job + services + VNC sessions, CPU is tight; profile early
- **Primary PDK for MVP:** SKY130 only — most community examples, most mature ORFS support
- **ORFS reliability strategy:** Pin ORFS image version; harden canary CI in Phase 2 (not Phase 1)
- **Open-source first:** Apache 2.0 license; any university should be able to deploy from README
- **Design data privacy:** GDS/DEF contents and student names/emails never sent to cloud LLMs
- **VNC is bandwidth-heavy:** Recommended for on-campus deployment; each session ~1-2 GB RAM
- **Celery architecture:** Dedicated ORFS job workers + dedicated background workers (tiles, grading, AI)
  — background tasks on "idle-only" queue are unreliable when all ORFS workers are busy

## Constraints

- **Tech Stack**: FastAPI (Python 3.12+), React + TypeScript, Celery + Redis, PostgreSQL 16, MinIO, Docker — finalized, do not change without discussion
- **Container Runtime**: Docker socket mount on worker host (simpler than DinD; security implications documented)
- **LLM Inference**: Ollama local-first (default); pluggable for Anthropic/OpenAI if needed
- **Storage**: MinIO locally, endpoint-switchable to S3 with same boto3 code
- **Auth**: JWT in memory (15min) + httpOnly refresh cookie (7 days); VNC uses separate scoped token
- **Package Management**: `uv` (Python), `npm` (TypeScript); `ruff` + `mypy` for Python linting
- **Tile Generation**: KLayout Python API as background Celery task; always keep fast-path single PNG

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SKY130 only for MVP | Most community examples, most mature ORFS support | — Pending |
| Pin ORFS image + canary CI | Broken ORFS mid-semester is catastrophic; pin prevents silent regressions | — Pending |
| ORFS reliability hardening in Phase 2, not Phase 1 | Get Phase 1 working first; build confidence before investing in shims | — Pending |
| noVNC → OpenROAD Qt GUI for interactive viewer | Full fidelity; weeks not months vs building a custom WebGL renderer | — Pending |
| MapLibre GL + KLayout tiles for static viewer | Proven tiled map approach; no GDS parser in the browser | — Pending |
| Celery dedicated queues for ORFS vs background tasks | Idle-only queue unreliable when ORFS workers are saturated | — Pending |
| Enrollment code: short alphanumeric (VLSI-2026-XK9T) | UUIDs unfriendly to share verbally in a lecture hall | — Pending |
| Tile zoom computed from design bounding box | Small GCD design doesn't need zoom 18; saves storage and generation time | — Pending |
| Show storage usage to students | Self-management reduces support tickets and confusing quota failures | — Pending |

---
*Last updated: 2026-03-12 after initialization*
