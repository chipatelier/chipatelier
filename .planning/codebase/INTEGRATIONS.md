# External Integrations

**Analysis Date:** 2025-03-13

## APIs & External Services

**OpenROAD Flow Scripts (ORFS):**
- Docker image: `openroad/orfs:latest` (configurable in `ORFS_IMAGE` env var)
- What it's used for: RTL-to-GDS flow execution; students submit Verilog + config, ORFS synthesizes/places/routes
- SDK/Client: Docker SDK for Python (`docker 7.1.x`); spawned containers run `make DESIGN_CONFIG=/workspace/config.mk`
- Container security: `network_mode="none"`, read-only filesystem, no capabilities, unprivileged user, cgroup resource limits
- Implementation: `worker/tasks/orfs_job.py` (run_orfs_job Celery task), `worker/container/manager.py` (ContainerManager)

**OpenROAD VNC Viewer:**
- Docker image: `chipatelier/vnc-viewer:latest` (built from `vnc-container/` directory)
- What it's used for: Interactive layout inspection via noVNC; students view DEF/GDS in OpenROAD GUI
- Tech stack inside container: Xvfb (X11 server), x11vnc, websockify, supervisord
- Pre-load: DEF + LEF files from completed ORFS runs mounted from MinIO artifacts
- Implementation: `worker/tasks/vnc_session.py` (start_vnc Celery task), `backend/app/api/routes/vnc.py` (VNC session API)
- WebSocket proxy: Nginx proxies `/vnc/{token}` → container:6080 (websockify)

**KLayout (Python API):**
- What it's used for: Generate tiled PNG images of GDS layouts for browser visualization
- Client: KLayout Python bindings (included in `openroad/orfs:latest` image)
- Implementation: `worker/tasks/tile_generator.py` (planned for phase 01-05, stub exists)
- Output: Tiles stored in MinIO at `tiles/{runId}/{layer}/{z}/{x}/{y}.png`

## Data Storage

**PostgreSQL 16:**
- Provider: PostgreSQL 16-alpine (Docker service: `postgres:16-alpine`)
- Connection: `postgresql+asyncpg://user:pass@postgres:5432/chipatelier` (from `DATABASE_URL` env var)
- Client: SQLAlchemy 2.0.x (async via asyncpg driver)
- ORM: SQLAlchemy declarative models in `backend/app/models/` (user, project, run, vnc_session)
- Migrations: Alembic (`backend/alembic/` directory; `alembic upgrade head` on startup)
- Critical tables:
  - `users` (auth, institution)
  - `projects` (course + user association)
  - `runs` (job status, metrics JSONB, config JSONB)
  - `vnc_sessions` (active viewer sessions)
- Indexes: GIN indexes on `runs.ppa` and `runs.config` JSONB for leaderboard queries

**Redis 7:**
- Provider: Redis 7-alpine (Docker service: `redis:7-alpine`)
- Connection: `redis://redis:6379/0` (from `REDIS_URL` env var)
- Client: redis-py 5.x (sync in worker, async in backend)
- Purpose:
  - **Celery broker**: Task queue for ORFS jobs and background work
  - **Results backend**: Task completion status
  - **Pub/Sub**: Log streaming to connected clients (`logs:{run_id}` channel)
  - **Buffering**: Last 5000 log lines stored in list `logbuf:{run_id}` (24h TTL)
- Implementation: `backend/app/core/redis.py`, `worker/celery_app.py`, `worker/celeryconfig.py`

**MinIO (S3-Compatible Storage):**
- Provider: MinIO (Docker service: `minio/minio:latest`)
- Endpoint: `minio:9000` (internal), `localhost:9001` (MinIO console, not used by API)
- Connection: boto3 S3 client with S3v4 signature (required for MinIO compatibility)
- Auth: `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` env vars
- Bucket: `chipatelier-artifacts`
- Purpose:
  - Upload/store Verilog source files, config.mk, constraints from students
  - Store ORFS run outputs: logs, reports, DEF, GDS, LEF files
  - Store tiled layout PNGs (per design layer and zoom level)
- Implementation: `backend/app/services/storage_service.py` (StorageService class)
- Key patterns:
  - `{project_id}/` — project source files
  - `runs/{run_id}/` — run artifacts (config snapshot, DEF, GDS, merged LEF)
  - `tiles/{run_id}/{layer}/{z}/{x}/{y}.png` — layout tiles (planned phase 01-05)

**File Storage (Alternative):**
- Local filesystem via Docker volumes (not used; artifacts always go to MinIO/S3)
- Workspace directories: `/tmp/workspace_{run_id}` on worker host (temporary; cleaned up after job completion)

## Authentication & Identity

**Auth Provider:**
- Type: Custom JWT-based (no external OAuth/SAML in MVP; planned for phase 3)
- Implementation: `backend/app/core/security.py`, `backend/app/api/routes/auth.py`
- Token format:
  - Access token: JWT with 15min expiry (in response body, not HttpOnly)
  - Refresh token: 7-day JWT in HttpOnly cookie (secure, SameSite=Strict)
  - VNC token: HMAC-signed JWT (separate secret `VNC_TOKEN_SECRET`, 2h expiry)
- Password hashing: Argon2id via argon2-cffi (memory-hard, timing-resistant)
- User model: `backend/app/models/user.py` (email, display_name, password_hash, institution_id)

**Authorization:**
- Pattern: Route-level `get_current_user` dependency (FastAPI Depends)
- Scope: Users can only access their own projects and runs
- Admin endpoints: Not yet implemented (phase 2)

## Monitoring & Observability

**Error Tracking:**
- Service: Not deployed (planned integration point, not yet used)
- Could be: Sentry, DataDog, or cloud provider native

**Logs:**
- Approach: Structured logging to stdout via Python logging module
- ORFS job logs: Streamed real-time to Redis pubsub (`logs:{run_id}` channel)
- Log buffering: Last 5000 lines in Redis list `logbuf:{run_id}` for replay
- Replay endpoint: `GET /api/v1/jobs/{id}/logs` (paginated historical log retrieval)
- Container logs: Docker stdout/stderr captured in `run_orfs_job` task and published to Redis

**Metrics:**
- Approach: Metrics extracted from ORFS logs and stored as JSONB in `runs.ppa` table
- Implementation: `backend/app/services/metrics_service.py` (log parsing, metric extraction)
- Captured metrics: worst_negative_slack (WNS), total_negative_slack (TNS), DRC violation count, cell counts, wirelength, power

## CI/CD & Deployment

**Hosting:**
- Platform: On-premise Docker Compose (default deployment)
- One-command deploy: `docker compose up -d`
- Scalability: Separate worker containers for ORFS jobs and background tasks
- Resource isolation: Celery queue routing (`orfs_jobs` vs `background` queues)

**CI Pipeline:**
- Service: Not configured (can be GitHub Actions, GitLab CI, etc.)
- Canary test requirement: New ORFS image versions must pass `gcd` design test before rollout
- Reference: `canary_reference.json` (not yet in repo; placeholder for CI/CD integration)

**Container Images:**
- `chipatelier-backend`: Built from `backend/Dockerfile`, published to internal registry or Docker Hub
- `chipatelier-worker`: Built from `worker/Dockerfile`, two instances in docker-compose (orfs-worker, background-worker)
- `chipatelier/vnc-viewer`: Built from `vnc-container/Dockerfile`
- Base images pinned: Python 3.12-slim, nginx:alpine, postgres:16-alpine, redis:7-alpine

## Environment Configuration

**Required Environment Variables:**
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` — PostgreSQL credentials
- `DATABASE_URL` — Full PostgreSQL async connection string
- `REDIS_URL` — Redis broker connection string
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` — MinIO credentials
- `STORAGE_BACKEND` — "minio" (default) or "s3"
- `JWT_SECRET_KEY` — Access token signing secret (change in production)
- `VNC_TOKEN_SECRET` — VNC session token signing secret (change in production)
- `ORFS_IMAGE` — Docker image tag (e.g., `openroad/orfs:latest`, pinned in production)
- `LLM_BACKEND` — "ollama" (default, local) or "anthropic"/"openai"
- `OLLAMA_BASE_URL` — Ollama endpoint for local LLM inference
- `ANTHROPIC_API_KEY` — Optional, for cloud LLM backend

**Secrets Location:**
- `.env` file (local development, never committed)
- Docker Compose: `env_file: .env` directive loads secrets into containers
- Production: Use Docker Compose `.env`, Kubernetes Secrets, or vault (future)

## Webhooks & Callbacks

**Incoming:**
- Not implemented (no external systems push events into ChipAtelier)

**Outgoing:**
- Not implemented (no callbacks to external services)
- Future integration point: Notify LMS (Canvas, Blackboard) of grade submissions (phase 3)

## Integration Architecture Overview

```
┌─ Browser (React) ──────────────────────────────────────┐
│  axios → /api/v1/... endpoints                         │
│  WebSocket → /api/v1/ws/... log streaming              │
└─────────────────────┬──────────────────────────────────┘
                      │
    ┌─────────────────┴────────────────────────────┐
    │                                              │
┌───▼────────────────────────────────┐   ┌────────▼───────────────────────┐
│ FastAPI Backend (app.main:app)     │   │ Nginx (reverse proxy)           │
│ ├─ auth routes                     │   │ ├─ /api → :8000 (backend)      │
│ ├─ projects routes                 │   │ ├─ /vnc/{token} → :6080+ (VNC) │
│ ├─ jobs routes (submit, status)    │   │ ├─ / → :3000 (frontend)        │
│ ├─ vnc routes (start, validate)    │   └────────────────────────────────┘
│ └─ WebSocket: /ws/logs/{run_id}    │
└────────┬────────────────────────────┘
         │
    ┌────┴─────┬──────────────┬──────────────┐
    │           │              │              │
┌───▼────┐  ┌──▼──────┐  ┌──▼─────────┐  ┌──▼────┐
│ Redis  │  │ Celery  │  │ PostgreSQL │  │MinIO/S3
│ (7)    │  │ Workers │  │ (16)       │  │
└────────┘  └────┬────┘  └────────────┘  └────────┘
                 │
         ┌───────┴────────┐
         │                │
    ┌────▼──────────┐  ┌──▼───────────┐
    │ ORFS Containers
    │ (orfs_job.py) │  │ VNC Containers
    │               │  │ (vnc_session.py)
    └───────────────┘  └────────────────┘
```

**Data Flow — Job Submission to Completion:**

1. **Frontend**: User uploads Verilog/config, clicks "Run"
2. **API** (`jobs.py`): POST `/api/v1/jobs/submit`
   - Validates project ownership
   - Creates `Run` record with status=`queued`
   - Uploads source files to MinIO (prefix: `runs/{run_id}/`)
   - Dispatches Celery task `tasks.orfs_job.run_orfs_job` to `orfs_jobs` queue
3. **ORFS Worker** (`orfs_job.py`):
   - Dequeues task, status → `starting`
   - Downloads workspace files from MinIO
   - Spawns Docker container with `openroad/orfs` image
   - Captures stdout/stderr, publishes each line to Redis pubsub `logs:{run_id}`
   - Stage transition detection inserts separators in log stream
   - Stores last 5000 lines in Redis list `logbuf:{run_id}`
   - Polls container.wait() for exit code
   - Status → `complete` (exit 0) or `failed` (exit ≠ 0)
   - Uploads artifacts (DEF, GDS, LEF, reports) back to MinIO
   - Parses metrics from log, stores in `runs.ppa` JSONB
   - Dispatches background task `tasks.tile_generator.generate_png` (phase 01-05)
   - Cleans up container and workspace directory in finally block
4. **Frontend** (WebSocket subscriber):
   - Connected to `/api/v1/ws/logs/{run_id}`
   - Receives each log line from Redis pubsub
   - Renders in xterm.js Terminal component
   - Stage transitions visualized as separator lines
5. **Leaderboard Query**:
   - `GET /api/v1/courses/{course_id}/leaderboard/{assignment_id}`
   - Queries `runs.ppa` JSONB (worst_negative_slack, etc.) via GIN index
   - Returns ranked list of students (anonymous)

---

*Integration audit: 2025-03-13*
