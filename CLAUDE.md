# CLAUDE.md — ChipAtelier

> This file provides full project context for Claude Code.
> Read this before writing any code. Update it when significant decisions are made.

---

## Project Summary

**ChipAtelier** is an open-source, web-based learning platform that gives university students
a fully managed RTL-to-GDS ASIC implementation environment using the OpenROAD toolchain.
Students log in through a browser portal, submit design jobs, view live logs, inspect layouts,
and receive AI-assisted feedback — no local EDA tool installation required.

- **License:** Apache 2.0
- **Repo:** github.com/chipatelier (public, to be created)
- **Target deployment:** Single on-premise university server (Docker Compose)
- **Primary PDKs:** SKY130, GF180, ASAP7

---

## Architecture Overview

```
Browser (React + TypeScript)
  ├── Main Portal Tab   — flow control, config editor, log stream, reports
  └── VNC Viewer Tab    — noVNC → OpenROAD Qt GUI (on demand, new tab)
          |
    REST + WebSocket
          |
FastAPI Backend
  ├── Job API           — submit, status, cancel, artifacts
  ├── Tile API          — layout viewer tile serving
  ├── Query API         — click-to-inspect on layout (OpenDB queries)
  ├── WebSocket         — real-time log streaming + stage events
  └── AI Service        — log explainer, config advisor, chat
          |
  ├── PostgreSQL 16     — metadata, metrics (JSONB), grades, users
  ├── Redis 7           — job queue (Celery broker) + pubsub (log streaming)
  ├── Celery Workers    — job orchestration, container lifecycle
  └── MinIO             — S3-compatible artifact storage
          |
ORFS Docker Containers  — one per running job, fully isolated
VNC Docker Containers   — one per active viewer session
```

---

## Repository Structure

```
chipatelier/
├── README.md                    # 5-minute deploy guide (most important file)
├── LICENSE                      # Apache 2.0
├── CONTRIBUTING.md
├── docker-compose.yml           # One-command full-stack deploy
├── .env.example                 # All required environment variables
│
├── frontend/                    # React + TypeScript
│   ├── src/
│   │   ├── components/
│   │   │   ├── FlowControlPanel/
│   │   │   ├── ConfigEditor/     # Monaco + form mode
│   │   │   ├── LogTerminal/      # xterm.js
│   │   │   ├── LayoutViewer/     # MapLibre GL + VNC launcher
│   │   │   ├── ReportsDashboard/
│   │   │   ├── AssignmentPanel/
│   │   │   └── Leaderboard/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── api/                  # API client (typed, axios-based)
│   │   └── store/                # Zustand state management
│   └── Dockerfile
│
├── backend/                     # FastAPI (Python 3.12+)
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── jobs.py
│   │   │   │   ├── projects.py
│   │   │   │   ├── users.py
│   │   │   │   ├── courses.py
│   │   │   │   ├── tiles.py
│   │   │   │   └── query.py
│   │   │   └── websocket.py      # Log streaming WS endpoint
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── schemas/              # Pydantic schemas
│   │   ├── services/
│   │   │   ├── job_service.py
│   │   │   ├── storage_service.py  # MinIO/S3 abstraction
│   │   │   ├── auth_service.py
│   │   │   └── quota_service.py
│   │   ├── core/
│   │   │   ├── config.py         # Settings (pydantic-settings)
│   │   │   ├── database.py       # PostgreSQL connection
│   │   │   ├── redis.py
│   │   │   └── security.py       # JWT, password hashing
│   │   └── main.py
│   ├── alembic/                  # DB migrations
│   ├── tests/
│   └── Dockerfile
│
├── worker/                      # Celery workers
│   ├── tasks/
│   │   ├── orfs_job.py          # Main ORFS execution task
│   │   ├── vnc_session.py       # VNC lifecycle management
│   │   ├── tile_generator.py    # KLayout tile generation
│   │   ├── checkpoint_eval.py   # Assignment grading
│   │   └── ai_hints.py          # Pre-generate AI hints
│   ├── container/
│   │   ├── manager.py           # Docker SDK wrapper
│   │   └── warm_pool.py         # Pre-started container pool
│   └── Dockerfile
│
├── ai-service/                  # FastAPI AI microservice (MVP: module in backend, split later)
│   ├── app/
│   │   ├── routes/
│   │   │   ├── explain.py        # /explain/log, /explain/timing, /explain/drc
│   │   │   ├── advisor.py        # /advisor/config
│   │   │   └── chat.py           # /chat (context-aware)
│   │   ├── prompts/              # Prompt templates per feature
│   │   ├── context_builder.py   # Injects run data into prompts
│   │   └── llm_client.py        # Pluggable: Ollama or cloud LLM
│   └── Dockerfile
│
├── vnc-container/               # noVNC + OpenROAD viewer image
│   ├── Dockerfile               # Based on openroad/orfs:latest
│   ├── supervisord.conf         # Xvfb + x11vnc + websockify
│   └── start_session.sh         # Load DEF/GDS on launch
│
├── assignments/                 # Community assignment library
│   ├── README.md
│   ├── lab-01-floorplan-basics/
│   │   ├── assignment.yaml      # Objectives, checkpoints, config
│   │   ├── design/              # Starter Verilog + SDC
│   │   └── README.md
│   └── lab-02-timing-closure/
│
├── infra/
│   ├── kubernetes/              # Helm chart
│   └── nginx/
│       └── nginx.conf           # Reverse proxy + VNC session routing
│
└── scripts/
    ├── install.sh               # One-command setup
    ├── backup.sh
    └── update.sh
```

---

## Key Technology Decisions (Do Not Change Without Discussion)

| Decision | Choice | Reason |
|---|---|---|
| Backend framework | FastAPI (Python) | Native OpenROAD Python API, async support |
| Job queue | Celery + Redis | Mature, fair queuing, Redis pubsub for log streaming |
| Database | PostgreSQL 16 | JSONB for metrics, pgvector future option |
| Object storage | MinIO (local) / S3 (cloud) | Same boto3 code, endpoint-switchable |
| Layout viewer | MapLibre GL + KLayout tile server | Proven tiled map approach, no GDS parser needed |
| Interactive viewer | noVNC → OpenROAD Qt GUI | Full fidelity, weeks not months to build |
| Container runtime | Docker (socket mount on worker host) | Simpler than DinD, sufficient for single server |
| Auth tokens | JWT (memory) + httpOnly refresh cookie | XSS protection, standard pattern |
| Frontend state | Zustand | Lightweight, no boilerplate |
| LLM inference | Ollama (local, default) | Design data stays on-premise |

---

## Database Schema (Core Tables)

```sql
-- Users & Auth
users (id UUID PK, email, display_name, institution_id, role, auth_provider,
       external_id, password_hash, is_active, created_at, last_login_at,
       storage_used_bytes, timezone, notification_prefs JSONB)

institutions (id UUID PK, name, domain_whitelist TEXT[], sso_config JSONB,
              storage_quota_bytes, created_at)

-- Courses & Assignments
courses (id UUID PK, institution_id, instructor_id, name, term, is_active)

course_enrollments (id UUID PK, course_id, user_id, enrolled_at)

assignments (id UUID PK, course_id, title, description, module_order,
             pdk, starter_design_id, locked_params JSONB, editable_params JSONB,
             target_stage, prerun_stage, checkpoint_rules JSONB,
             due_at TIMESTAMPTZ, orfs_version)

-- Projects & Runs
projects (id UUID PK, user_id, course_id, assignment_id, name, pdk,
          storage_bytes, created_at)

source_versions (id UUID PK, project_id, verilog TEXT, sdc TEXT,
                 config_mk TEXT, version_num INT, created_at)

runs (id UUID PK, project_id, source_version_id, status TEXT,
      target_stage, stage_completed TEXT, is_submitted BOOL,
      is_starred BOOL, notes TEXT, artifact_path TEXT,
      ppa JSONB,       -- PPA metrics only: WNS, TNS, DRC, power, wirelength
      config JSONB,    -- config.mk snapshot: CLOCK_PERIOD, CORE_UTILIZATION etc.
      stage_metrics JSONB,  -- per-stage runtimes, cell counts
      storage_bytes BIGINT, created_at, completed_at, expires_at)

-- GIN indexes for frequent instructor/leaderboard queries:
-- CREATE INDEX idx_runs_ppa ON runs USING GIN (ppa);
-- CREATE INDEX idx_runs_config ON runs USING GIN (config);
-- Specific path indexes for hot queries:
-- CREATE INDEX idx_runs_wns ON runs ((ppa->>'worst_negative_slack'));
-- CREATE INDEX idx_runs_clock ON runs ((config->>'CLOCK_PERIOD'));

-- Grading
submissions (id UUID PK, run_id, assignment_id, user_id,
             checkpoint_results JSONB, score NUMERIC, submitted_at)

-- VNC Sessions
vnc_sessions (id UUID PK, user_id, run_id, container_id, port INT,
              status TEXT, token TEXT, created_at, expires_at)
```

---

## API Endpoints (Key Routes)

```
POST   /api/v1/jobs/submit              Submit a flow job
GET    /api/v1/jobs/{id}               Job status + metrics
GET    /api/v1/jobs/{id}/logs          Log history (paginated)
WS     /api/v1/jobs/{id}/logs/stream   Live log stream
DELETE /api/v1/jobs/{id}               Cancel running job

GET    /api/v1/projects                List user projects
POST   /api/v1/projects                Create project
GET    /api/v1/projects/{id}/runs      List runs for project
POST   /api/v1/projects/{id}/runs/{rid}/submit   Submit for grading

GET    /api/v1/tiles/{runId}/{layer}/{z}/{x}/{y}.png   Tile server
GET    /api/v1/query/{runId}?x=&y=&layer=             Click-to-query

POST   /api/v1/vnc/start/{runId}       Start VNC session → returns token
DELETE /api/v1/vnc/{sessionId}         End VNC session

POST   /api/v1/ai/explain/log         Explain log failure
POST   /api/v1/ai/explain/timing      Explain timing path
POST   /api/v1/ai/advisor/config      Config suggestions
POST   /api/v1/ai/chat                Context-aware chat

GET    /api/v1/courses/{id}/leaderboard/{assignmentId}   Anonymous rankings
GET    /api/v1/admin/queue             Job queue status (admin)
```

---

## Environment Variables (.env)

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/chipatelier

# Redis
REDIS_URL=redis://redis:6379/0

# Storage
STORAGE_BACKEND=minio               # minio | s3
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
S3_BUCKET_ARTIFACTS=chipatelier-artifacts

# Auth
JWT_SECRET_KEY=change_me_in_production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
VNC_TOKEN_SECRET=change_me_in_production

# OpenROAD
ORFS_IMAGE=openroad/orfs:latest
PDK_ROOT=/data/pdks
ARTIFACTS_ROOT=/data/artifacts
WARM_POOL_SIZE=4
MAX_CONCURRENT_JOBS=12
JOB_TIMEOUT_SECONDS=7200           # 2 hours max per job

# Resource limits (per student job)
JOB_CPU_CORES=6
JOB_RAM_GB=8
JOB_DISK_GB=5

# VNC session limits
MAX_VNC_SESSIONS=8                 # tune per server RAM (each ~1-2GB + OpenROAD)

# Worker configuration
ORFS_WORKER_CONCURRENCY=4         # dedicated ORFS job workers
BACKGROUND_WORKER_CONCURRENCY=2   # dedicated background task workers (tiles, grading, AI hints)

# AI Service
LLM_BACKEND=ollama                 # ollama | anthropic | openai
OLLAMA_BASE_URL=http://ai-service:11434
ANTHROPIC_API_KEY=                 # optional, for cloud LLM

# Domain
ALLOWED_ORIGINS=https://your.university.edu
```

---

## Job States

```
queued → starting → running → [complete | failed | timeout | cancelled]
```

States are stored in both PostgreSQL (durable) and Redis (live). Redis heartbeat from
worker every 30 seconds. If heartbeat stops for > 2 minutes, job is requeued.

---

## ORFS Container Lifecycle

```python
# Worker spawns container per job:
docker run \
  --name orfs_job_{run_id} \
  --network none \                    # CRITICAL: no network access
  --cpus {JOB_CPU_CORES} \
  --memory {JOB_RAM_GB}g \
  --memory-swap {JOB_RAM_GB}g \       # No swap
  --read-only --tmpfs /tmp \
  --user orfs:orfs \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  -v {workspace}:/workspace:rw \
  -v {pdk_root}:/pdks:ro \
  --storage-opt size={JOB_DISK_GB}G \
  openroad/orfs:{version}
```

Always cleaned up in finally block — no orphaned containers.

---

## VNC Container Setup

```bash
# Inside vnc-container:
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
x11vnc -display :99 -nopw -listen localhost -xkb &
websockify --web /usr/share/novnc/ 6080 localhost:5900 &

# Pre-load student's DEF/GDS into OpenROAD:
openroad -gui -no_splash << EOF
read_lef $LEF_FILE
read_def $DEF_FILE
EOF
```

Nginx proxies `/vnc/{token}` → container port 6080. Token validated before proxying.

---

## Log Streaming Architecture

```
Container stdout → LogStreamer (Python thread)
                       ├── Redis PUBLISH logs:{run_id}   (live)
                       ├── Batch write to disk (100 lines)
                       └── Stage transition detection → DB update

FastAPI WebSocket endpoint:
  GET /api/v1/jobs/{id}/logs/stream
  → Redis SUBSCRIBE logs:{run_id}
  → Push each line to browser (xterm.js)
```

---

## Checkpoint Evaluation

Assignment checkpoint rules are stored as JSONB in the `assignments` table:

```json
{
  "hard": [
    {"metric": "drc_violations", "op": "eq", "value": 0},
    {"metric": "flow_complete", "op": "eq", "value": true}
  ],
  "scored": [
    {"metric": "worst_negative_slack", "op": "gte", "value": -0.1,
     "points": 40, "partial": {"threshold": -0.5, "points": 20}},
    {"metric": "total_negative_slack", "op": "gte", "value": -1.0,
     "points": 30}
  ]
}
```

Evaluated in `checkpoint_eval.py` Celery task after job completion.
Results stored in `submissions` table. Student notified via WebSocket push.

---

## Tile Generation

Tiles generated by KLayout Python API as background Celery task after job completion.
Stored in MinIO at `tiles/{runId}/{layer}/{z}/{x}/{y}.png`.

Layers rendered separately: `metal1`, `metal2`, `metal3`, `via1`, `via2`, `cells`, `pins`, `macros`.
Zoom levels: 0–18 (capped at design scale — not all zoom levels needed for small designs).

Frontend uses MapLibre GL to composite layers client-side with toggle/opacity controls.

---

## AI Service — Prompt Templates

Each AI feature has a prompt template in `ai-service/app/prompts/`.
Context builder (`context_builder.py`) injects:
- Current stage name
- Last N lines of log (configurable per feature)
- Parsed metrics from metrics.json
- Current config.mk contents
- Design name + PDK

**What NEVER goes to cloud LLMs:**
- GDS or DEF file contents
- PDK files or data
- Student names or email addresses

---

## Authentication Flow

```
Login (any method)
  → POST /api/v1/auth/login or SSO redirect
  → Returns: access_token (15min JWT, in response body)
             refresh_token (7 day, httpOnly cookie)

All API requests: Authorization: Bearer {access_token}

Token refresh: POST /api/v1/auth/refresh (uses httpOnly cookie)
  → Returns new access_token

VNC session: POST /api/v1/vnc/start/{runId}
  → Returns scoped VNC token (separate secret, 2hr expiry)
  → Frontend opens /vnc/{token} in new tab
  → Nginx validates token, proxies to container port
```

---

## Assignment Library Format

Each assignment in `assignments/` follows this structure:

```yaml
# assignment.yaml
id: lab-timing-closure-01
title: "Lab 2.1 — Timing-Driven Placement"
module: "Placement & Timing"
difficulty: 3
pdk: sky130hd
design: picorv32
target_stage: route
orfs_version: "latest"

locked_params:
  - CLOCK_PERIOD
  - PLATFORM

editable_params:
  - CORE_UTILIZATION
  - PLACE_DENSITY
  - TNS_END_PERCENT

checkpoints:
  hard:
    - metric: drc_violations
      op: eq
      value: 0
  scored:
    - metric: worst_negative_slack
      op: gte
      value: -0.1
      points: 40

hints:
  - trigger: "high_congestion_placement"
    text: "Check your placement congestion map. Try increasing CELL_PAD or reducing CORE_UTILIZATION."
  - trigger: "timing_violation_large"
    text: "WNS is very negative. Check if CLOCK_PERIOD is realistic for this design at this utilization."
```

---

## CI / CD Requirements

**CRITICAL: ORFS canary test on every image bump.**
A broken ORFS image rolling out mid-semester is catastrophic.

```yaml
# .github/workflows/orfs-canary.yml
# Triggers on: new ORFS image tag, or weekly schedule
- name: Run canary design
  run: |
    docker run openroad/orfs:{new_version} \
      make DESIGN_CONFIG=designs/sky130hd/gcd/config.mk
    # Assert: flow completes, DRC=0, WNS within tolerance of reference
```

- Use `gcd` design on `sky130hd` — fastest complete flow (~3 min)
- Store reference metrics (WNS, DRC count) in repo as `canary_reference.json`
- Fail CI if new image deviates by > 10% on any metric
- Pin `ORFS_IMAGE` in `.env` to last passing canary version — never auto-update

---

## MVP Scope (Build First)

Phase 1 — Core flow (weeks 1-6):
- [ ] Docker Compose stack (all services running)
- [ ] User auth (local accounts only — SSO in v2)
- [ ] Project creation + Verilog/config upload
- [ ] Job submission → ORFS container → log streaming → artifact storage
- [ ] Basic flow control panel (stage status, run/cancel)
- [ ] Static layout snapshot (single PNG from KLayout, not tiles)
- [ ] VNC viewer integration (noVNC tab, DEF pre-loaded)

Phase 2 — Learning layer (weeks 7-12):
- [ ] Tiled layout viewer (MapLibre GL + KLayout tile generation)
- [ ] Assignment system (create, enroll, submit, auto-grade checkpoints)
- [ ] Anonymous leaderboard
- [ ] Config editor with form mode
- [ ] Run comparison view
- [ ] Instructor dashboard

Phase 3 — AI + polish (weeks 13-18):
- [ ] AI log explainer (Ollama integration)
- [ ] AI config advisor
- [ ] AI chat with context injection
- [ ] SSO (SAML 2.0 + OIDC)
- [ ] Storage quota enforcement + retention cleanup
- [ ] Admin panel

---

## Development Conventions

- Python: `uv` for package management, `ruff` for linting, `mypy` for type checking
- TypeScript: strict mode, ESLint + Prettier
- All API schemas typed end-to-end (Pydantic → OpenAPI → generated TypeScript client)
- Database migrations: Alembic, never edit tables manually
- Tests: pytest for backend (target 80% coverage), Vitest for frontend
- Commits: conventional commits (`feat:`, `fix:`, `docs:`, `chore:`)
- All secrets via environment variables — never in code or git

---

## Known Constraints

- ORFS routing jobs are CPU and RAM heavy — enforce cgroup limits strictly
- KLayout tile generation is slow (2-5 min) — always run as background task,
  but ALWAYS keep the fast-path single PNG overview (seconds) as permanent
  preview while tiles build. Do not remove this after Phase 1.
- noVNC is bandwidth-heavy — recommend on-campus deployment for VNC viewer
- PostgreSQL metrics JSONB: use GIN index on frequently queried keys
  (`CLOCK_PERIOD`, `CORE_UTILIZATION`, `worst_negative_slack`). Config
  should be a separate JSONB column from PPA metrics to simplify filtering.
- Ollama model loading takes 5-15s on first request — warm on startup
- Docker socket mount on worker has security implications — document clearly,
  consider rootless Docker or Podman for hardened deployments
- DL380 Gen9 CPU budget is tight: dual E5-2600 = 28-36 cores total.
  At 4-8 cores/job + Celery + Redis + PostgreSQL + MinIO + AI service +
  VNC sessions, you may hit CPU limits before the 30-40 student target.
  Profile a realistic mixed workload in Phase 1. Deployment docs should
  recommend EPYC or Xeon Scalable for production deployments.
- Celery background queue ("idle workers only") is unreliable if all workers
  are busy with ORFS jobs. Use a DEDICATED background worker process
  (1-2 concurrency) separate from the ORFS job workers.

---

## Resolved Design Decisions (from spec review)

1. **Enrollment code format:** Short alphanumeric — `VLSI-2026-XK9T` style (6-8 chars,
   safe alphabet, collision-checked on creation). UUIDs are unfriendly to share verbally
   in a lecture hall.

2. **VNC session limits:** Configurable via `.env` — `MAX_VNC_SESSIONS=8` default.
   Each session costs ~1-2 GB RAM + Xvfb/OpenROAD CPU. Right limit depends on available
   resources, so must be tunable per deployment.

3. **Tile zoom levels:** Compute optimal max zoom from design bounding box — do NOT
   generate all 0-18 levels. A small GCD design doesn't need zoom 18. Store
   `max_useful_zoom` in run metadata so the frontend knows when to stop requesting tiles.
   Formula: `max_zoom = ceil(log2(max(width_um, height_um) / MIN_FEATURE_SIZE_UM))`

4. **Storage visibility:** YES — show students their usage (`1.2 GB of 5 GB used`)
   in the dashboard. Self-management reduces support tickets and avoids confusing
   quota-exceeded job failures.

5. **First PDK:** SKY130 only for MVP. Most community examples, most mature ORFS
   support. GF180 and ASAP7 in Phase 2 — no architectural changes needed.
