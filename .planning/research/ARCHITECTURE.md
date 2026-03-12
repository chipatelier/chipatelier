# Architecture Research

**Domain:** Web-based ASIC education platform (job orchestration, log streaming, layout visualization, VNC sessions)
**Researched:** 2026-03-12
**Confidence:** HIGH — architecture derived from CLAUDE.md spec decisions + established patterns for this class of system

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (React + TypeScript)                                    │
│  ├── Main Portal — flow control, config editor, logs, reports   │
│  └── VNC Tab — noVNC WebSocket → OpenROAD Qt GUI                │
└──────────────────┬──────────────────────────────────────────────┘
                   │  REST (axios) + WebSocket
┌──────────────────▼──────────────────────────────────────────────┐
│  Nginx (reverse proxy)                                           │
│  ├── /api/v1/* → FastAPI                                        │
│  └── /vnc/{token} → VNC container port 6080 (token-validated)  │
└──────────────────┬──────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│  FastAPI Backend                                                 │
│  ├── Job API (submit, status, cancel, artifacts)                │
│  ├── Tile API (KLayout tile serving from MinIO)                 │
│  ├── Query API (click-to-inspect via OpenDB)                    │
│  ├── WebSocket (log streaming via Redis pub/sub)                │
│  └── AI Service (log explainer, config advisor, chat)           │
└──┬──────────┬──────────┬──────────────────────────────────────--┘
   │          │          │
   ▼          ▼          ▼
PostgreSQL   Redis       MinIO
(metadata)  (broker +   (artifacts +
            pub/sub)     tiles)
               │
┌──────────────▼──────────────────────────────────────────────────┐
│  Celery Workers                                                  │
│  ├── orfs_jobs queue (4 workers) — ORFS container lifecycle     │
│  └── background queue (2 workers) — tiles, grading, AI hints   │
└──┬──────────────────────────────────────────────────────────────┘
   │
   ├── ORFS Docker Containers (one per job, --network none)
   └── VNC Docker Containers (one per viewer session)
```

## Component Responsibilities

| Component | Responsibility | Key Interfaces |
|-----------|---------------|----------------|
| FastAPI | Request routing, auth, WebSocket hub, tile proxy | REST endpoints, WS /jobs/{id}/logs/stream |
| Celery `orfs_jobs` | ORFS container spawn, log capture, artifact storage, heartbeat | Redis broker, Docker socket |
| Celery `background` | Tile generation (KLayout), checkpoint eval, AI hint pre-gen | Redis broker, MinIO, PostgreSQL |
| PostgreSQL | Durable state: users, jobs, courses, assignments, metrics, scores | SQLAlchemy async sessions |
| Redis | Live job state, Celery broker, log pub/sub channels `logs:{run_id}` | redis-py async client |
| MinIO | Artifact blobs (GDS, DEF, reports), tile PNGs | aioboto3, path: `artifacts/{runId}/`, `tiles/{runId}/` |
| Nginx | TLS termination, reverse proxy, VNC token validation | Upstream: FastAPI :8000, VNC containers dynamic ports |
| ORFS Container | Isolated RTL-to-GDS flow execution | stdin/stdout only; `--network none`; volume mounts for workspace + PDKs |
| VNC Container | Xvfb + x11vnc + websockify + OpenROAD pre-loaded | Port 6080 (WebSocket); launched by Celery vnc task |

## Architectural Patterns

### 1. Container-Per-Job Isolation

```
Celery worker
  → docker run --name orfs_job_{run_id} --network none ...
  → attach stdout/stderr
  → LogStreamer thread:
      ├── PUBLISH to Redis logs:{run_id}  (live)
      ├── batch write to disk (100-line buffer)
      └── detect stage transitions → UPDATE runs.stage_completed
  → finally: docker rm orfs_job_{run_id}  # always cleaned up
```

**Build order note:** Container lifecycle must be solid before any UI work — orphaned containers are the hardest failure mode to recover from.

### 2. Real-Time Log Streaming (Redis Pub/Sub)

```
ORFS container stdout
  → LogStreamer Python thread (in Celery worker process)
  → Redis PUBLISH logs:{run_id}  (each log line as message)

FastAPI WebSocket endpoint /api/v1/jobs/{id}/logs/stream
  → Redis SUBSCRIBE logs:{run_id}
  → push each message to browser WebSocket
  → browser: xterm.js renders ANSI-colored output

On disconnect + reconnect:
  → client requests log history from PostgreSQL (paginated)
  → then resubscribes to live channel
```

**Critical:** Redis channel must have TTL or LTRIM to prevent unbounded growth. Log history stored to disk/DB in batches, not kept in Redis.

### 3. Two-Phase Layout Delivery

```
Phase A (fast, seconds): Static PNG overview
  → KLayout generates single overview PNG immediately after job completes
  → Stored in MinIO: artifacts/{runId}/layout_preview.png
  → Frontend shows this immediately while tiles generate

Phase B (slow, 2-5 min): Tiled viewer
  → Celery background worker runs KLayout tile generation
  → Tiles stored: tiles/{runId}/{layer}/{z}/{x}/{y}.png
  → max_useful_zoom computed from design bounding box
  → Frontend polls for tile availability; upgrades viewer when ready
```

**Critical:** Phase A and Phase B paths must be strictly separate. Never block Phase A on tile generation. Never remove Phase A after Phase 2 ships.

### 4. Celery Queue Architecture

```
# Two dedicated worker processes (not routing modes):

Process 1 — ORFS jobs:
  celery -A worker worker -Q orfs_jobs -c 4

Process 2 — Background tasks:
  celery -A worker worker -Q background -c 2

# Task routing:
orfs_job.run → orfs_jobs queue
tile_generator.generate → background queue
checkpoint_eval.evaluate → background queue
ai_hints.generate → background queue

# Why separate: background tasks starve if all orfs_jobs workers busy
```

### 5. VNC Session Lifecycle

```
Client: POST /api/v1/vnc/start/{runId}
  → Celery task: docker run vnc-container
      --env DEF_FILE={path} --env LEF_FILE={path}
      → container starts Xvfb + x11vnc + websockify
      → OpenROAD pre-loads DEF/LEF
  → Generate scoped VNC token (separate secret, 2hr expiry)
  → Store in vnc_sessions table
  → Return token to client

Client opens: /vnc/{token} in new tab
  → Nginx validates token → proxy to container port 6080
  → noVNC WebSocket → x11vnc → Xvfb → OpenROAD Qt GUI

Cleanup:
  → Session expiry (2hr): Celery scheduled task kills container
  → Manual close: DELETE /api/v1/vnc/{sessionId}
  → Worker crash: watchdog task checks orphaned containers
```

### 6. Artifact Storage Paths (MinIO)

```
artifacts/
  {runId}/
    verilog/              # uploaded source
    reports/
      *.rpt               # timing, DRC, power reports
    gds/
      {design}.gds
    def/
      {stage}.def         # multiple stages
    logs/
      flow.log            # full run log
    metadata/
      metrics.json        # PPA metrics (WNS, TNS, DRC, power)
      config_snapshot.mk  # config used for this run

tiles/
  {runId}/
    {layer}/              # metal1, metal2, via1, cells, pins, macros
      {z}/{x}/{y}.png
    layout_preview.png    # fast-path overview (always present first)
```

## Anti-Patterns

| Anti-Pattern | Why Dangerous | Correct Approach |
|--------------|---------------|------------------|
| Single Celery queue | Background tasks starve during ORFS load | Dedicated `orfs_jobs` + `background` queues |
| Redis for log history | Redis memory exhaustion; data loss on restart | Disk + DB for history; Redis for live only |
| Synchronous Docker operations in FastAPI | Blocks event loop; kills request throughput | All container ops go through Celery tasks |
| Storing GDS/DEF in PostgreSQL | TOAST bloat; wrong tool for binary blobs | MinIO only; PostgreSQL stores paths |
| Generating all zoom levels 0-18 | Tiny GCD design + zoom 18 = thousands of useless tiles | Compute `max_useful_zoom` from design bbox |
| VNC token = session UUID | UUID is guessable/forgeable | Separate HMAC-signed token with VNC_TOKEN_SECRET |

## Build Order (Dependency Sequence)

```
1. Infrastructure       — Docker Compose: postgres, redis, minio, nginx
2. Database schema      — Alembic migrations: users, projects, runs tables
3. Auth                 — JWT login/register endpoints + middleware
4. Job submission       — REST endpoint → Celery task → ORFS container spawn
5. Log streaming        — Redis pub/sub pipeline + WebSocket endpoint
6. Artifact storage     — MinIO upload in Celery worker + download endpoint
7. Static layout PNG    — KLayout single-PNG generation (fast path)
8. Frontend shell       — React app: auth, project list, basic job view
9. VNC integration      — VNC container lifecycle + Nginx token routing
10. Tile pipeline       — KLayout tile generation Celery task + MapLibre GL viewer
11. Assignment system   — Courses, enrollments, checkpoint eval, grading
12. AI service          — Ollama integration, prompt templates, log explainer
```

**Critical dependency:** Steps 1-6 must all work before building any UI. The WebSocket + Celery + Redis pipeline is the hardest integration point; validate it with a test job before building UI on top of it.

## Integration Boundaries

### Internal (within Docker Compose network)
- FastAPI ↔ PostgreSQL: SQLAlchemy async (asyncpg driver)
- FastAPI ↔ Redis: redis-py async client
- FastAPI ↔ MinIO: aioboto3
- Celery worker ↔ Docker daemon: Python docker SDK (socket mount)
- Celery worker ↔ Redis: Celery Redis broker
- Nginx ↔ FastAPI: HTTP proxy to port 8000
- Nginx ↔ VNC containers: dynamic port proxy, token in URL

### External (browser)
- Browser ↔ Nginx: HTTPS (port 443)
- Browser ↔ FastAPI WebSocket: `wss://host/api/v1/jobs/{id}/logs/stream`
- Browser ↔ VNC container (via Nginx): `wss://host/vnc/{token}`
- Browser ↔ MapLibre GL tiles: `GET /api/v1/tiles/{runId}/{layer}/{z}/{x}/{y}.png`

---
*Architecture research for: ChipAtelier ASIC education platform*
*Researched: 2026-03-12*
