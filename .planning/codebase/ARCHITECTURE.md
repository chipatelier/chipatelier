# Architecture

**Analysis Date:** 2026-03-13

## Pattern Overview

**Overall:** Distributed asynchronous job processing architecture with separate frontend, API server, and isolated container-based job workers.

**Key Characteristics:**
- **Async/await backend** (FastAPI) for request handling with dependency injection
- **Distributed job queue** (Celery + Redis) with dedicated worker pools for different task types
- **Container-per-job isolation** (Docker SDK, network=none, read-only filesystem)
- **Real-time log streaming** (Redis pub/sub + WebSocket) with client-side replay buffer
- **Metadata-driven state** (PostgreSQL + JSONB for metrics/config) with Redis for ephemeral state

## Layers

**Presentation Layer:**
- Purpose: React TypeScript UI for user interaction and real-time job monitoring
- Location: `frontend/src/`
- Contains: React components (Flow control, logs, layout viewer), Zustand state, typed API client
- Depends on: HTTP/REST and WebSocket to backend API
- Used by: Browser clients

**API Layer:**
- Purpose: Expose REST endpoints for job lifecycle, authentication, and project management
- Location: `backend/app/api/routes/` and `backend/app/websocket.py`
- Contains: FastAPI route handlers with async request processing, WebSocket endpoint for log streaming
- Depends on: Database (async queries), Redis (pub/sub and log buffering), Celery client (task dispatch)
- Used by: Frontend client, external integrations

**Business Logic / Services Layer:**
- Purpose: Encapsulate domain logic (storage abstraction, metrics parsing, authentication)
- Location: `backend/app/services/`
- Contains: `StorageService` (MinIO/S3 wrapper), `MetricsService` (PPA parsing), auth service, log parser
- Depends on: Configuration, boto3 (S3), external systems
- Used by: API routes and background tasks

**Data Layer:**
- Purpose: Persistent state storage and ephemeral state management
- Location: `backend/app/core/` (database.py, redis.py), `backend/app/models/`
- Contains: SQLAlchemy async ORM engine, Redis connection pool, model definitions (Run, Project, User, etc.)
- Depends on: PostgreSQL, Redis network connectivity
- Used by: All layers

**Job Execution Layer:**
- Purpose: Long-running ORFS container jobs with isolated execution and resource limits
- Location: `worker/tasks/orfs_job.py`, `worker/container/manager.py`, `worker/celery_app.py`
- Contains: Celery task definition, Docker SDK wrapper for container lifecycle, stage transition detection
- Depends on: Docker daemon (socket mount), PostgreSQL (status updates), Redis (log publishing), MinIO (source/artifact storage)
- Used by: Backend API (via task dispatch), Celery worker processes

**Background Tasks Layer:**
- Purpose: Non-critical, asyncable work (PNG generation, tile generation, VNC sessions, watchdog cleanup)
- Location: `worker/tasks/tile_generator.py`, `worker/tasks/vnc_session.py`, `worker/tasks/watchdog.py`
- Contains: Celery task implementations for post-job artifact generation, VNC session lifecycle, orphaned container cleanup
- Depends on: Database, Redis, storage, Docker daemon
- Used by: Celery background worker, scheduled beat tasks

## Data Flow

**Job Submission Flow:**

1. **Frontend (UI)** → User clicks "Submit" button with project config
2. **Frontend (API client)** → `POST /api/v1/jobs/submit` with `SubmitRequest` (project_id, target_stage, config_overrides)
3. **Backend (jobs.py)** → Validates project ownership, enforces single-active-run constraint, creates Run record with status="queued"
4. **Backend (celery_client.py)** → Dispatches `tasks.orfs_job.run_orfs_job(run_id)` to Celery (routing: "orfs_jobs" queue)
5. **Redis** → Task enqueued in "orfs_jobs" queue
6. **Backend (response)** → Returns `SubmitResponse(run_id, status="queued")` with 202 Accepted
7. **Frontend (store)** → Updates Zustand job slice: `setActiveRun(run_id)`, `setRunStatus("queued")`

**Job Execution Flow:**

1. **ORFS Worker** → Dequeues task from "orfs_jobs" queue (concurrency: 4)
2. **Worker (orfs_job.py)** → Calls `run_orfs_job(run_id)` Celery task
3. **Worker** → Creates `/tmp/workspace_{run_id}/` directory
4. **Worker (manager.py)** → Downloads source files (Verilog, SDC, config.mk) from MinIO to workspace
5. **Worker (manager.py)** → Spawns ORFS container with `docker run` (isolated: network=none, read-only, mem/cpu limits)
6. **ORFS Container** → Executes `make DESIGN_CONFIG=/workspace/config.mk` (6 stages: synthesis, floorplan, place, cts, route, gds)
7. **Container → Worker (log stream)** → Each stdout/stderr line is:
   - Pattern-matched against `STAGE_PATTERNS` for stage transitions
   - Published to Redis channel `logs:{run_id}` (pub/sub for live subscribers)
   - Appended to Redis list `logbuf:{run_id}` (LRU-capped at 5000 lines, 24hr TTL for replay)
   - Stage completion updates PostgreSQL `runs.stage_completed`
8. **Container completes** → Exit code 0 = "complete", non-zero = "failed"
9. **Worker (finally block)** → ALWAYS stops and removes container, removes workspace directory (invariant enforced)

**Log Streaming to Frontend:**

1. **Frontend** → User opens job detail page, connects WebSocket: `WS /api/v1/ws/jobs/{run_id}/logs/stream?token={JWT}`
2. **Backend (websocket.py)** → Validates JWT token from query param (cannot use headers in WS)
3. **Backend** → Accepts WebSocket connection
4. **Backend** → Fetches full buffered log from `logbuf:{run_id}` Redis list (handles late joiners)
5. **Backend** → Replays all buffered lines to client (TCP order preserved)
6. **Backend** → Subscribes to Redis channel `logs:{run_id}` and pushes each new line to WebSocket as it arrives
7. **Frontend (LogTerminal component)** → Renders each line in xterm.js emulator
8. **Frontend (jobSlice)** → On stage transition separators, updates `stageProgress` for visual indicator
9. **On disconnect** → Backend unsubscribes from Redis pub/sub and closes connection

**Artifact Generation Flow (Background Task):**

1. **Worker (orfs_job.py, line 179)** → After container exit (success), calls `generate_png.delay(run_id, workspace)` (non-blocking)
2. **Background Worker** → Dequeues from "background" queue (concurrency: 2)
3. **Worker (tile_generator.py)** → Finds GDS/DEF in `workspace/results/{platform}/{design}/`
4. **Worker (tile_generator.py)** → Renders 2048×2048 PNG using KLayout Python API (headless, no X11)
5. **Worker (tile_generator.py)** → Uploads PNG + GDS + DEF to MinIO at `runs/{run_id}/layout.png`, `runs/{run_id}/6_final.gds`, `runs/{run_id}/6_final.def`
6. **Worker (tile_generator.py)** → Parses `metadata.json` to extract PPA metrics (WNS, TNS, DRC, area, power)
7. **Worker (tile_generator.py)** → Updates Run record: `artifact_path`, `ppa`, `stage_metrics` in PostgreSQL

**State Management:**

- **Durable State** (PostgreSQL): Run status, stage_completed, metrics (ppa), config snapshot
- **Ephemeral State** (Redis): Log buffer (logbuf:{run_id}, 24hr TTL), live pubsub (logs:{run_id}), Celery task queue and results
- **Local State** (Frontend/Zustand): activeRunId, runStatus, stageProgress computed from stageCompleted

## Key Abstractions

**Run Model:**
- Purpose: Represents one ORFS job execution with full lifecycle tracking
- Examples: `backend/app/models/run.py`
- Pattern: SQLAlchemy ORM with JSONB columns for metrics (ppa, config, stage_metrics) and separate indexed fields for common queries (status, stage_completed, created_at)

**ContainerManager:**
- Purpose: Abstracts Docker container lifecycle (spawn, monitor, cleanup)
- Examples: `worker/container/manager.py`
- Pattern: Singleton-like manager that uses Docker SDK; enforces security constraints (network=none, read-only, cap_drop=ALL, user=orfs:orfs, cgroup limits); guarantees cleanup in finally block

**StorageService:**
- Purpose: Abstracts MinIO/S3 object storage with presigned URLs and batch operations
- Examples: `backend/app/services/storage_service.py`
- Pattern: Dependency-injected service wrapping boto3 with s3v4 signature (required for MinIO compatibility); used for artifact upload/download

**MetricsService:**
- Purpose: Parses ORFS metadata.json (METRICS2.1 format) into normalized PPA dict
- Examples: `backend/app/services/metrics_service.py`
- Pattern: Standalone function + class wrapper for DI; maps ORFS field names to human-readable keys (timing__setup__ws → worst_negative_slack)

**Celery Task Routing:**
- Purpose: Separates CPU-heavy ORFS jobs from lightweight background tasks to prevent starvation
- Examples: `worker/celeryconfig.py`, `worker/tasks/orfs_job.py`, `worker/tasks/tile_generator.py`
- Pattern: Two dedicated worker processes (orfs-worker, background-worker) listening to different queues; celeryconfig.task_routes direct tasks to the correct queue

## Entry Points

**API Server:**
- Location: `backend/app/main.py`
- Triggers: `docker compose up` → FastAPI uvicorn server on 0.0.0.0:8000
- Responsibilities: Register route handlers, CORS setup, lifespan (init DB, close Redis), health check endpoint

**ORFS Worker Process:**
- Location: `worker/celery_app.py` + `worker/celeryconfig.py`
- Triggers: `docker compose up` → Celery worker `-Q orfs_jobs` with concurrency=4
- Responsibilities: Dequeue orfs_job tasks, spawn containers, stream logs to Redis, update run status

**Background Worker Process:**
- Location: `worker/celery_app.py` + `worker/celeryconfig.py`
- Triggers: `docker compose up` → Celery worker `-Q background` with concurrency=2
- Responsibilities: Dequeue background tasks (PNG gen, tiles, VNC, watchdog), update DB

**Frontend App:**
- Location: `frontend/src/` (no explicit entry point file; built as SPA)
- Triggers: Browser navigates to http://localhost:8080 (served by nginx)
- Responsibilities: Render React components, manage Zustand state, connect to backend API and WebSocket

## Error Handling

**Strategy:** Fail gracefully with user-facing error messages and comprehensive logging; never cascade failures.

**Patterns:**

- **Celery Task Failures** (`worker/tasks/orfs_job.py`, line 183–186):
  - Catch all exceptions, update status to "failed", publish failure message to log stream
  - Container is ALWAYS stopped in finally block (even on exception)
  - Workspace is ALWAYS cleaned up in finally block
  - Task is not retried (job is terminal once failed — user must resubmit)

- **Log Stream Errors** (`backend/app/websocket.py`, line 42–44):
  - Invalid or expired JWT: close WebSocket with code 4008
  - Connection drop: cleanly unsubscribe from Redis pub/sub
  - Unreachable Redis: connection errors propagate to client as disconnect

- **Storage Errors** (`worker/tasks/tile_generator.py`, line 99–105):
  - KLayout import missing: log warning and continue (skip PNG, upload GDS/DEF anyway)
  - MinIO unreachable: silently skip (artifact_path may remain None, GDS/DEF download links unavailable)
  - Metadata parse errors: return defaults (don't crash job completion)

- **Database Errors** (`backend/app/api/routes/jobs.py`, line 62–76):
  - Project not found: 404 Not Found
  - Project not owned by user: 403 Forbidden
  - Run already active: 409 Conflict
  - Database unavailable: 503 Service Unavailable (from healthz check)

## Cross-Cutting Concerns

**Logging:**
- **Backend:** Python logging module; each route and service logs at INFO/WARNING/ERROR levels
- **Worker:** Celery and custom task loggers; worker logs published to Redis pub/sub for real-time UI streaming
- **Frontend:** Console.log and error boundaries; errors displayed in toast notifications

**Validation:**
- **API Input:** Pydantic schemas (`backend/app/schemas/`) validate and convert all incoming JSON (type safety, bounds checks)
- **Database:** SQLAlchemy ORM models define column constraints (nullable, unique, FK references); Alembic migrations ensure schema consistency
- **Frontend:** TypeScript strict mode + typed API client; form validation in components before submission

**Authentication:**
- **JWT Access Tokens:** 15-minute expiry, stored in response body, passed in Authorization header
- **JWT Refresh Tokens:** 7-day expiry, httpOnly cookie, used to obtain new access token
- **WebSocket:** JWT passed as `?token=` query param (browsers cannot set custom headers); token validated before accepting connection
- **VNC Tokens:** Separate scoped token (2hr expiry) for VNC session access (stored in Redis, validated by nginx proxy)

**Authorization:**
- **Project Ownership:** All endpoints requiring project/run access check `project.user_id == current_user.id`
- **Single-Active-Run:** Enforced at submit time to prevent user from having > 1 queued/running job per project
- **Role-Based Access:** User model has `role` field (instructor, student); future phases add course enrollment checks

**Resource Limits (per job):**
- **CPU:** 6 cores (configurable via `JOB_CPU_CORES` env var, enforced via cgroup cpu_quota)
- **RAM:** 8 GB (configurable via `JOB_RAM_GB`, no swap allowed to prevent thrashing)
- **Disk:** 5 GB (configurable via `JOB_DISK_GB`, storage-opt requires overlay2+pquota mount on RHEL; currently disabled, enforce via OS quotas)
- **Timeout:** 2 hours (configurable via `JOB_TIMEOUT_SECONDS`; container.wait() enforces hard limit)

**Secrets Management:**
- All secrets passed via environment variables (DATABASE_URL, REDIS_URL, JWT_SECRET_KEY, MINIO credentials, VNC_TOKEN_SECRET)
- Never hardcoded in source; .env file in repo root (git-ignored) for development
- Production: secrets provided by deployment orchestrator (Docker Swarm, Kubernetes, Nomad secrets store)

---

*Architecture analysis: 2026-03-13*
