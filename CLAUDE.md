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
# NOTE: PDK_ROOT is NOT used by ORFS — it is an OpenLane variable. Do not add it here.
# Platform files (sky130hd, gf180, asap7) are bundled inside the openroad/orfs image
# at /OpenROAD-flow-scripts/flow/platforms/. No external PDK mount is needed.
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

## ORFS Flow Invocation

ORFS is a **Make-based framework**. The worker wraps `make`, not a Python/Tcl API directly.

```bash
# Primary invocation inside the ORFS container:
# WORK_HOME redirects ALL output (results/, logs/, reports/, objects/) to /workspace.
# Without WORK_HOME, output goes relative to the make working directory — not /workspace.
make --file=/OpenROAD-flow-scripts/flow/Makefile \
     DESIGN_CONFIG=/workspace/config.mk \
     WORK_HOME=/workspace \
     [TARGET]

# Stage targets (cumulative — runs up to and including this stage):
make synth        # synthesis only      → results/.../1_synth.odb
make floorplan    # up to floorplan     → results/.../2_floorplan.odb
make place        # up to placement     → results/.../3_place.odb
make cts          # up to CTS           → results/.../4_cts.odb
make route        # up to routing       → results/.../5_route.odb
make finish       # full flow to GDS    → results/.../6_final.gds
# 'final' is an alias for 'finish'. 'grt'/'globalroute' runs only GRT sub-step.

# Clean individual stages (enables re-run from that stage):
make clean_synth | clean_floorplan | clean_place | clean_cts | clean_route | clean_finish
# Pattern for re-run from a stage:
make clean_route && make DESIGN_CONFIG=... WORK_HOME=/workspace route
# NOTE: clean_route also removes route.guide and output_guide.mod

# GUI targets — open OpenROAD Qt GUI with stage ODB pre-loaded:
make gui_floorplan | gui_place | gui_cts | gui_route | gui_final

# Locking parameters via command-line override (highest priority — ignores config.mk):
make --file=... DESIGN_CONFIG=... WORK_HOME=/workspace \
     CLOCK_PERIOD=10 PLATFORM=sky130hd route
```

**`DESIGN_HOME` and `DESIGN_NICKNAME` are valid ORFS variables:**
- `DESIGN_HOME` defaults to `/OpenROAD-flow-scripts/flow/designs` — root for design source files
- `DESIGN_NICKNAME` defaults to `DESIGN_NAME` — controls output subdirectory name
- For student workspaces use absolute paths in config.mk instead of relying on DESIGN_HOME:
  ```makefile
  export VERILOG_FILES = /workspace/src/mydesign.v
  export SDC_FILE      = /workspace/constraint.sdc
  ```

**Results directory** (all paths relative to `WORK_HOME`, i.e. `/workspace`):
```
results/{PLATFORM}/{DESIGN_NICKNAME}/base/
  1_synth.v              # gate-level netlist (Yosys output)
  1_synth.sdc            # post-synthesis timing constraints
  1_synth.odb            # OpenDB binary — synthesis→floorplan handoff
  2_floorplan.odb        # OpenDB after floorplan
  2_floorplan.sdc
  3_place.odb            # OpenDB after placement
  4_cts.odb              # OpenDB after CTS
  5_route.odb            # OpenDB after routing
  6_final.gds            # final GDSII (KLayout generated)
  6_final.def            # final DEF (only DEF written at finish)
  6_final.v              # final netlist with physical cells
  6_final.sdc

logs/{PLATFORM}/{DESIGN_NICKNAME}/base/
  1_1_yosys_canonicalize.log
  1_2_yosys.log
  1_2_yosys.json              # synthesis metrics
  2_1_floorplan.log
  2_1_floorplan.json          # floorplan metrics (keys: floorplan__*)
  3_1_place_gp_skip_io.json
  3_3_place_gp.json           # global placement metrics (keys: globalplace__*)
  3_4_place_resized.json      # post-resize metrics (keys: placeopt__*)
  3_5_place_dp.json           # detail placement metrics (keys: detailedplace__*)
  4_1_cts.log
  4_1_cts.json                # CTS metrics (keys: cts__*)
  5_1_grt.log
  5_1_grt.json                # global route metrics (keys: globalroute__*)
  5_2_route.json              # detail route metrics (keys: detailedroute__*)
  5_3_fillcell.json
  6_report.log
  6_report.json               # ← FINAL SIGNOFF METRICS (keys: finish__*)

  # GRT failure indicator — present when global route fails with congestion:
  # 5_1_grt-failed.odb written instead of 5_1_grt.odb; exit code may still be 0
  # MUST check for this file in addition to exit code to detect GRT congestion failure

reports/{PLATFORM}/{DESIGN_NICKNAME}/base/
  final_all.webp         # ← ORFS auto-generates these — no KLayout work needed
  final_routing.webp
  final_placement.webp
  final_clocks.webp
  final_ir_drop.webp
  final_congestion.webp  # congestion heatmap — free, use directly as stage preview
  final_resizer.webp
  final_worst_path.webp
  cts_{clock}_layout.webp  # one per clock domain
```

**genMetrics.py** — ORFS ships a utility at `flow/util/genMetrics.py` that merges all
per-stage JSON files into a single `metadata.json`. Use this after job completion to
get a unified metrics dict instead of reading individual stage files manually.

**CRITICAL: The primary artifact format is `.odb` not `.def`.**
ODB is OpenROAD's binary database. DEF is only written at finish.
All intermediate stage inspection loads `.odb` files.

## ORFS Container Lifecycle

```bash
# Docker run flags for ORFS job container:
docker run \
  --name orfs_job_{run_id} \
  --network none \                     # CRITICAL: no internet access; ORFS needs none
  --cpus {JOB_CPU_CORES} \            # nproc inside container respects this; OpenROAD auto-threads
  --memory {JOB_RAM_GB}g \
  --memory-swap {JOB_RAM_GB}g \        # No swap
  --cap-drop ALL \
  --security-opt no-new-privileges \
  -v {workspace}:/workspace:rw \       # student workspace (results/logs/reports written here)
  --tmpfs /tmp:size=2g \               # Yosys uses /tmp during synthesis; 2g safe for small designs
  openroad/orfs:{version} \
  make --file=/OpenROAD-flow-scripts/flow/Makefile \
       DESIGN_CONFIG=/workspace/config.mk \
       WORK_HOME=/workspace \
       {target}
```

**Container user notes:**
- The `openroad/orfs` image runs as **root by default** (no USER directive in Dockerfile)
- The image does `chmod o+rw -R /OpenROAD-flow-scripts` — world-writable installation dir
- Running as a non-root user (e.g. `--user 1000:1000`) is safe as long as the workspace
  volume is writable by that UID
- Do NOT use `--read-only` on the container root — OpenROAD may write temp files outside
  WORK_HOME; security is provided by `--network none` + cgroup limits instead

**PDK notes:**
- Do NOT mount an external PDK volume. The `openroad/orfs` image contains all platform
  files for sky130hd, gf180, and asap7 at `/OpenROAD-flow-scripts/flow/platforms/`
- `PDK_ROOT` is an OpenLane variable — it is NOT used by ORFS. Remove it from invocations.
- Platform config is auto-loaded via `PLATFORM_DIR=$(FLOW_HOME)/platforms/$(PLATFORM)`

**Memory estimates (sky130hd, small design like GCD):**

| Stage | Peak RAM |
|-------|----------|
| synth (yosys) | ~200–400 MB |
| floorplan | ~400–600 MB |
| place | ~600 MB–1 GB |
| cts | ~500–700 MB |
| route (GRT+DRT) | ~1–2 GB |
| finish | ~500 MB–1 GB |

For larger designs (picorv32, ibex), routing can peak at 4–8 GB. Set `JOB_RAM_GB`
based on the largest design students are expected to run.

**storage-opt note:** `--storage-opt size=Xg` requires overlay2 + `pquota` mount on
RHEL/Rocky 9. Until that is configured, enforce disk at the OS level (filesystem quotas
on the workspace directory).

Always cleaned up in finally block — no orphaned containers.

---

## VNC Container Setup (Corrected)

The GUI loads `.odb` files via ORFS's own `open.tcl` script — NOT `read_def`.
The Make `gui_*` targets show the exact mechanism:

```bash
# Inside vnc-container — replicate what `make gui_cts` does:
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
x11vnc -display :99 -nopw -listen localhost -xkb &
websockify --web /usr/share/novnc/ 6080 localhost:5900 &

# Set env vars ORFS open.tcl expects, then launch GUI:
export DESIGN_CONFIG=/workspace/config.mk
export ODB_FILE=/workspace/results/sky130hd/{design}/base/{stage}.odb
export OPENROAD_EXE=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad

$OPENROAD_EXE -gui /OpenROAD-flow-scripts/flow/scripts/open.tcl

# open.tcl sources load.tcl and calls:
#   source $::env(SCRIPTS_DIR)/load.tcl
#   load_design $ODB_FILE $SDC_FILE
# This correctly loads the full design context including LEF/LIB.
```

Stage-to-ODB mapping for VNC pre-loading:
```python
STAGE_ODB = {
    "floorplan": "2_floorplan.odb",
    "place":     "3_place.odb",
    "cts":       "4_cts.odb",
    "route":     "5_route.odb",
    "finish":    "6_final.odb",   # or load 6_final.gds via KLayout
}
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

**Real ORFS log format** — OpenROAD uses structured log prefixes:
```
[INFO  <TOOL>-<NUM>] message
[WARNING <TOOL>-<NUM>] message
[ERROR <TOOL>-<NUM>] message
```
Common tool codes: `FLW` (flow), `FP` (floorplan), `GPL` (global place), `DPL` (detail place),
`CTS`, `GRT` (global route), `DRT` (detail route), `ORD` (OpenROAD core), `ODB` (OpenDB).

**Reliable stage transition detection** — `flow.sh` prints this line before every stage:
```
Running <script>.tcl, stage <stage_id>
```
Examples:
```
Running floorplan.tcl, stage 2_1_floorplan
Running cts.tcl, stage 4_1_cts
Running global_route.tcl, stage 5_1_grt
Running final_report.tcl, stage 6_report
```
Parse this pattern instead of guessing content-based patterns. The `stage_id` field maps
directly to the JSON metrics filename (e.g., `stage 2_1_floorplan` → `2_1_floorplan.json`).

**GRT failure detection** — global route can fail with congestion but exit 0:
- Failure writes `results/.../5_1_grt-failed.odb` instead of `5_1_grt.odb`
- Check for the `-failed.odb` suffix in results dir to detect GRT congestion failure
- Subsequent `detail_route` step will then fail with non-zero exit code

---

## Real ORFS Metrics Schema

ORFS writes per-stage JSON files in `logs/{platform}/{design}/base/` via the `-metrics`
flag passed to each OpenROAD invocation. Keys follow `{stage_prefix}__{category}__{metric}`.

**Stage prefix mapping** (file name → JSON key prefix):

| Log file | JSON key prefix | Written by |
|----------|-----------------|------------|
| `2_1_floorplan.json` | `floorplan__` | `floorplan.tcl` |
| `3_3_place_gp.json` | `globalplace__` | `global_place.tcl` |
| `3_4_place_resized.json` | `placeopt__` | `resize.tcl` |
| `3_5_place_dp.json` | `detailedplace__` | `detail_place.tcl` |
| `4_1_cts.json` | `cts__` | `cts.tcl` |
| `5_1_grt.json` | `globalroute__` | `global_route.tcl` |
| `5_2_route.json` | `detailedroute__` | `detail_route.tcl` |
| `6_report.json` | `finish__` | `final_report.tcl` ← primary signoff |

**Verified real key names** (from `flow/designs/ihp-sg13g2/i2c-gpio-expander/metadata-base-ok.json`):

```json
{
  "floorplan__timing__setup__ws": 0.0148687,
  "floorplan__timing__setup__tns": 0,
  "floorplan__timing__hold__ws": 0.0997134,
  "floorplan__timing__hold__tns": 0,
  "floorplan__power__total": 0.00202447,
  "floorplan__design__die__area": 1262.03,
  "floorplan__design__core__area": 1070.65,
  "floorplan__design__instance__count": 499,
  "floorplan__design__instance__utilization": 0.577391,
  "floorplan__design__io": 54,

  "cts__timing__setup__ws": -2.27,
  "cts__timing__setup__tns": -95.5,
  "cts__timing__hold__ws": -0.055,
  "cts__timing__hold__tns": -0.22,
  "cts__design__violations": 0,

  "globalroute__timing__setup__ws": -2.42,
  "globalroute__timing__setup__tns": -99.7,

  "detailedroute__route__drc_errors": 0,
  "detailedroute__route__wirelength": 37033,
  "detailedplace__design__violations": 0,

  "finish__timing__setup__ws": 3.88761,
  "finish__timing__setup__tns": 0,
  "finish__timing__hold__ws": 0.033864,
  "finish__timing__hold__tns": 0,
  "finish__power__total": 7.30843e-05,
  "finish__power__internal__total": 5.79117e-05,
  "finish__power__switching__total": 1.32977e-05,
  "finish__power__leakage__total": 1.87494e-06,
  "finish__design__instance__area": 118272
}
```

The metrics parser must:
1. Run `flow/util/genMetrics.py` after job completion to merge all per-stage JSON files
   into a single `metadata.json` (or read and merge the individual files manually)
2. Store merged dict as JSONB in PostgreSQL `runs.stage_metrics` column
3. Map to friendly names for `runs.ppa` column:

```python
METRIC_MAP = {
    # Final signoff WNS/TNS come from 6_report.json (finish__ prefix)
    # Fall back to globalroute if finish not yet written (partial run)
    "worst_negative_slack": lambda m: m.get("finish__timing__setup__ws",
                                   m.get("globalroute__timing__setup__ws", None)),
    "total_negative_slack": lambda m: m.get("finish__timing__setup__tns",
                                   m.get("globalroute__timing__setup__tns", None)),
    "core_utilization":     lambda m: m.get("floorplan__design__instance__utilization", None),
    # DRC routing errors — from detailed route, NOT "finish__design__violations" (that key doesn't exist)
    "drc_routing_errors":   lambda m: m.get("detailedroute__route__drc_errors", 0),
    # Placement violations are separate from routing DRC
    "placement_violations": lambda m: m.get("detailedplace__design__violations", 0),
    "total_power":          lambda m: m.get("finish__power__total", None),
    "die_area":             lambda m: m.get("floorplan__design__die__area", None),
    "core_area":            lambda m: m.get("floorplan__design__core__area", None),
    "wirelength":           lambda m: m.get("detailedroute__route__wirelength", None),
}
```

**CRITICAL: `finish__design__violations` does not exist in real ORFS output.**
DRC routing errors = `detailedroute__route__drc_errors`. Placement violations =
`detailedplace__design__violations`. KLayout DRC (from `make drc`) writes a text
report `reports/6_drc_count.rpt` — not a JSON key.

## Checkpoint Evaluation

Assignment checkpoint rules stored as JSONB in the `assignments` table.
Evaluated against the friendly-name mapped metrics above:

```json
{
  "hard": [
    {"metric": "drc_violations",  "op": "eq",  "value": 0},
    {"metric": "flow_complete",   "op": "eq",  "value": true}
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

## config.mk — Required Variables and Priority

Minimum required design config.mk (confirmed from ORFS docs):
```makefile
export PLATFORM      = sky130hd
export DESIGN_NAME   = gcd
export VERILOG_FILES = $(sort $(wildcard ./designs/src/gcd/*.v))
export SDC_FILE      = ./designs/sky130hd/gcd/constraint.sdc
export CORE_UTILIZATION  = 40
export PLACE_DENSITY     = 0.60
export TNS_END_PERCENT   = 100
```

Variable priority (highest wins):
1. Make command line: `make CLOCK_PERIOD=10`  ← use this to LOCK instructor params
2. Shell environment variables
3. settings.mk (local overrides, not in git)
4. Design config.mk (student editable)
5. Platform config.mk (sky130hd defaults — do not expose to students)
6. variables.yaml (~1000 variables, internal defaults)

ORFS has ~1000 configurable variables. ChipAtelier must curate a safe subset:
- Exposed to students: CORE_UTILIZATION, PLACE_DENSITY, TNS_END_PERCENT,
  CLOCK_PERIOD, CORE_ASPECT_RATIO, CORE_MARGIN, SETUP_SLACK_MARGIN
- Locked via Make command line (not editable even if in config.mk):
  PLATFORM, PDK_ROOT (instructor sets these at job invocation time)
- Hidden entirely: all platform variables (TECH_LEF, SC_LEF, LIB_FILES etc.)

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

## ORFS Workspace Directory Structure

When Make runs, results are written relative to the Make working directory:
```
/workspace/                          ← Make working directory (student project root)
  config.mk                          ← student's design config
  designs/src/{design}/
    design.v                         ← Verilog source
    constraint.sdc                   ← SDC timing constraints
  results/sky130hd/{design}/base/    ← all ODB/GDS outputs
  logs/sky130hd/{design}/base/       ← all logs + per-stage JSON metrics
  reports/sky130hd/{design}/base/    ← auto-generated WebP images
  objects/sky130hd/{design}/base/    ← KLayout layer file etc.
```

config.mk path references must resolve relative to /workspace.
PLATFORM is set in config.mk — results subdir is derived from it automatically.

## CTS Stage Details (Stage 4)

CTS runs four sub-steps inside a single `make cts` invocation:
1. **TritonCTS buffer insertion** — builds balanced H-tree clock network
2. **repair_timing** — fixes setup/hold violations with REAL clock delays
   (placement timing was based on ideal clock — CTS reveals true violations)
3. **Detailed placement re-run** — legalises newly inserted buffer cells
4. **Filler cell insertion** — fills empty standard cell row gaps for DRC

Students often see WNS worsen after CTS because the ideal clock assumption
is removed. The AI hint system must specifically detect and explain this pattern.
Output: `4_cts.odb` — load via `make gui_cts` or `load_design 4_cts.odb 4_cts.sdc`

## Known Constraints

- ORFS routing jobs are CPU and RAM heavy — enforce cgroup limits strictly
- KLayout tile generation is slow (2-5 min) — always run as background task.
  HOWEVER: ORFS already auto-generates WebP overview images at the finish stage
  (final_all.webp, final_routing.webp, final_placement.webp, final_congestion.webp,
  final_clocks.webp, final_ir_drop.webp) in reports/{platform}/{design}/base/.
  Serve these directly as the fast-path preview — no KLayout work needed for overview.
  Only build the full tile pyramid for the interactive zoom viewer.
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
