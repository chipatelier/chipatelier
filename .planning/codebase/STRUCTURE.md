# Codebase Structure

**Analysis Date:** 2026-03-13

## Directory Layout

```
chipatelier/
├── README.md                    # Quick start and overview
├── LICENSE                      # Apache 2.0
├── CONTRIBUTING.md              # Contribution guidelines
├── CLAUDE.md                    # Full project context (MUST read before coding)
├── docker-compose.yml           # Single-command full-stack deployment (dev/stage)
├── .env.example                 # Template for environment variables
│
├── frontend/                    # React + TypeScript SPA
│   ├── src/
│   │   ├── index.tsx            # React entry point (ReactDOM.render)
│   │   ├── App.tsx              # Root component with router
│   │   ├── pages/               # Page components (routed via react-router)
│   │   ├── components/          # Reusable UI components
│   │   │   ├── FlowControlPanel/
│   │   │   ├── LogTerminal/     # xterm.js wrapper for live logs
│   │   │   ├── LayoutSnapshot/  # KLayout PNG viewer
│   │   │   ├── RunHistoryTable/
│   │   │   └── StageStatusBar/  # Visual ORFS stage progress
│   │   ├── api/                 # Typed API client (axios-based)
│   │   │   ├── client.ts        # Axios instance + interceptors
│   │   │   ├── jobs.ts          # Job endpoints (submit, status, cancel, logs)
│   │   │   ├── projects.ts      # Project CRUD
│   │   │   └── auth.ts          # Login, token refresh, logout
│   │   ├── hooks/               # Custom React hooks (useWebSocket, usePolling)
│   │   ├── store/               # Zustand state management
│   │   │   ├── appStore.ts      # Root store (combines slices)
│   │   │   ├── jobSlice.ts      # Active run, stage progress
│   │   │   ├── authSlice.ts     # Current user, tokens
│   │   │   └── projectSlice.ts  # Project list, current project
│   │   └── styles/              # Global CSS, theme
│   ├── Dockerfile               # Node build + nginx serve
│   ├── package.json
│   ├── tsconfig.json            # Strict mode enabled
│   ├── vite.config.ts           # Vite build config (or webpack)
│   └── .eslintrc / .prettierrc   # Linting and formatting config
│
├── backend/                     # FastAPI (Python 3.12+)
│   ├── app/
│   │   ├── main.py              # FastAPI app setup, router registration, lifespan
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── jobs.py      # POST/GET/DELETE /jobs/* endpoints
│   │   │   │   ├── projects.py  # GET/POST /projects endpoints
│   │   │   │   ├── users.py     # GET /users/me endpoint
│   │   │   │   ├── auth.py      # POST /auth/login, /auth/refresh, /auth/logout
│   │   │   │   ├── artifacts.py # GET /artifacts/{run_id}/* download links (plan 01-05)
│   │   │   │   └── vnc.py       # POST /vnc/start/{run_id}, DELETE /vnc/{session_id} (plan 01-06)
│   │   │   ├── deps.py          # Dependency injection helpers (get_current_user, get_db)
│   │   │   └── websocket.py     # WS /ws/jobs/{run_id}/logs/stream endpoint
│   │   ├── models/              # SQLAlchemy ORM models
│   │   │   ├── base.py          # Base class with common fields (id, created_at)
│   │   │   ├── user.py          # User model (email, hashed_password, institution_id, role)
│   │   │   ├── project.py       # Project model (user_id FK, name, pdk, storage_bytes)
│   │   │   ├── run.py           # Run model (project_id FK, status, stage_completed, ppa, config, etc.)
│   │   │   ├── vnc_session.py   # VncSession model (user_id, run_id, container_id, port, token)
│   │   │   └── submission.py    # Submission model (for assignment grading, plan 01-07)
│   │   ├── schemas/             # Pydantic schemas for API validation/serialization
│   │   │   ├── jobs.py          # SubmitRequest, RunStatusResponse, etc.
│   │   │   ├── projects.py      # CreateProjectRequest, ProjectResponse, etc.
│   │   │   ├── users.py         # UserResponse, UpdateProfileRequest, etc.
│   │   │   └── auth.py          # LoginRequest, TokenResponse, etc.
│   │   ├── services/            # Business logic and external integrations
│   │   │   ├── storage_service.py # StorageService (MinIO/S3 wrapper)
│   │   │   ├── auth_service.py   # Authentication and password hashing (plan 01-02)
│   │   │   ├── metrics_service.py # PPA metrics parsing from ORFS metadata.json
│   │   │   └── log_parser.py     # Log line parsing for stage detection (plan 01-03)
│   │   ├── core/                # Infrastructure / core utilities
│   │   │   ├── config.py        # Pydantic Settings — all env vars loaded here
│   │   │   ├── database.py      # SQLAlchemy async engine, AsyncSessionLocal, get_db()
│   │   │   ├── redis.py         # Redis async connection pool, get_redis()
│   │   │   ├── celery_client.py # Celery app for task dispatch (send_task only, not workers)
│   │   │   ├── security.py      # JWT encode/decode, password hashing, token validation
│   │   │   └── exceptions.py    # Custom exception classes (plan 01-04)
│   │   └── utils/               # Utility functions (plan 01-04)
│   │       ├── validators.py    # Input validation helpers
│   │       └── formatters.py    # Response formatting utilities
│   ├── alembic/                 # Database migrations (Alembic managed)
│   │   ├── versions/
│   │   │   ├── 001_initial_schema.py
│   │   │   └── ...
│   │   ├── env.py               # Alembic config
│   │   └── alembic.ini
│   ├── tests/                   # pytest tests
│   │   ├── conftest.py          # Fixtures (test_db, test_redis, etc.)
│   │   ├── test_jobs.py         # Tests for job routes
│   │   ├── test_projects.py     # Tests for project routes
│   │   ├── test_auth.py         # Tests for authentication
│   │   └── ...
│   ├── Dockerfile               # Python 3.12 + dependencies
│   ├── requirements.txt          # Python dependencies (or pyproject.toml with uv)
│   └── .env.example             # Example env file (dev defaults)
│
├── worker/                      # Celery workers (Python, same runtime as backend)
│   ├── tasks/
│   │   ├── __init__.py          # Task package entry point
│   │   ├── orfs_job.py          # @app.task run_orfs_job(run_id) — main job executor
│   │   ├── tile_generator.py    # @app.task generate_png(run_id, workspace) — PNG/artifact generation
│   │   ├── vnc_session.py       # @app.task start_vnc_session(run_id), stop_vnc_session(session_id) (plan 01-06)
│   │   └── watchdog.py          # @app.task cleanup_orphaned_containers() — beat task for orphaned cleanup
│   ├── container/               # Docker management
│   │   ├── __init__.py
│   │   └── manager.py           # ContainerManager class (spawn, monitor, cleanup)
│   ├── celery_app.py            # Celery app instance with autodiscover_tasks(["tasks"])
│   ├── celeryconfig.py          # Celery configuration (broker, task routing, beat schedule)
│   ├── Dockerfile               # Python 3.12 + Docker SDK + KLayout (for PNG gen)
│   └── requirements.txt         # Worker-specific dependencies (celery, docker, klayout, etc.)
│
├── vnc-container/               # noVNC + OpenROAD GUI container (spawned by worker, not run by compose)
│   ├── Dockerfile               # Based on openroad/orfs:latest with noVNC/x11vnc overlay
│   ├── supervisord.conf         # Manages Xvfb, x11vnc, websockify
│   ├── start_session.sh         # Load DEF/GDS into OpenROAD on startup
│   └── README.md                # Build and usage instructions
│
├── infra/                       # Infrastructure and deployment
│   ├── nginx/
│   │   ├── nginx.conf           # Reverse proxy (API + frontend + VNC session routing)
│   │   └── README.md
│   ├── kubernetes/              # Helm chart for k8s deployment (plan 02-01)
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   └── scripts/                 # DevOps scripts
│
├── assignments/                 # Community assignment library
│   ├── README.md                # Assignment format specification
│   ├── lab-01-floorplan-basics/
│   │   ├── assignment.yaml      # Metadata: PDK, checkpoints, locked_params, target_stage
│   │   ├── design/              # Starter Verilog, SDC, constraints
│   │   └── README.md
│   └── lab-02-timing-closure/
│       └── ...
│
├── scripts/                     # Utility scripts
│   ├── install.sh               # One-command setup
│   ├── backup.sh                # Database + artifact backup
│   ├── update.sh                # Update ORFS image with canary test
│   └── dev_setup.sh             # Local dev environment setup
│
└── .planning/                   # GSD planning documents
    ├── codebase/                # Architecture & conventions (this directory)
    │   ├── ARCHITECTURE.md
    │   ├── STRUCTURE.md
    │   └── ... (other docs)
    ├── phases/                  # Implementation phase plans
    │   ├── 01-core-flow/
    │   │   ├── 01-UAT.md        # User acceptance tests
    │   │   └── ...
    │   └── ...
    └── research/                # Technical spikes and research docs
```

## Directory Purposes

**`frontend/src/`**
- Purpose: React TypeScript source code
- Contains: Components (UI + logic), pages (routed views), API client, state management (Zustand)
- Key files: `index.tsx` (entry), `App.tsx` (root), `pages/` (views), `api/jobs.ts` (job API client), `store/jobSlice.ts` (job state)

**`backend/app/`**
- Purpose: FastAPI backend source code
- Contains: REST API routes, SQLAlchemy ORM models, Pydantic schemas, business logic services, core infrastructure (DB, Redis, security)
- Key files: `main.py` (app setup), `api/routes/jobs.py` (job endpoints), `models/run.py` (Run ORM), `core/database.py` (async engine), `core/celery_client.py` (task dispatch)

**`backend/app/api/routes/`**
- Purpose: All REST endpoint handlers (FastAPI routes)
- Contains: One file per domain area (jobs.py, projects.py, auth.py, users.py, artifacts.py, vnc.py)
- Key files: `jobs.py` (submit, status, cancel, logs), `projects.py` (CRUD), `auth.py` (login, refresh)

**`backend/app/models/`**
- Purpose: SQLAlchemy ORM model definitions
- Contains: One file per table (user.py, project.py, run.py, vnc_session.py, submission.py)
- Key files: `run.py` (ORFS job execution record), `project.py` (student project), `user.py` (user auth)

**`backend/app/schemas/`**
- Purpose: Pydantic schemas for request/response validation and serialization
- Contains: One file per domain (jobs.py, projects.py, users.py, auth.py) with request/response DTO classes
- Key files: `jobs.py` (SubmitRequest, RunStatusResponse), `auth.py` (LoginRequest, TokenResponse)

**`backend/app/services/`**
- Purpose: Business logic, not request/response handling
- Contains: Reusable services (StorageService, MetricsService, AuthService, LogParser)
- Key files: `storage_service.py` (MinIO abstraction), `metrics_service.py` (PPA parsing), `auth_service.py` (password hashing, JWT)

**`backend/app/core/`**
- Purpose: Infrastructure and cross-cutting concerns
- Contains: Settings, database engine, Redis pool, Celery client, security utilities
- Key files: `config.py` (Settings from env vars), `database.py` (async SQLAlchemy engine), `redis.py` (async Redis pool), `celery_client.py` (task dispatch), `security.py` (JWT, password hashing)

**`worker/tasks/`**
- Purpose: Celery task implementations
- Contains: Long-running ORFS job task, background tasks (PNG gen, tiles, VNC, watchdog)
- Key files: `orfs_job.py` (main job executor), `tile_generator.py` (PNG + artifact upload), `vnc_session.py` (VNC lifecycle), `watchdog.py` (orphaned cleanup)

**`worker/container/`**
- Purpose: Docker container lifecycle management
- Contains: `ContainerManager` class wrapping Docker SDK for spawn, monitor, cleanup
- Key files: `manager.py` (run_container, stop_and_remove, list_orfs_containers)

**`backend/alembic/`**
- Purpose: Database migration management (Alembic)
- Contains: Migration scripts (one per schema change) + env.py (Alembic config)
- Key files: `versions/*.py` (migration files), `alembic.ini` (Alembic settings)

**`backend/tests/`**
- Purpose: pytest test suite
- Contains: Unit tests for routes, services, models + integration tests with fixtures
- Key files: `conftest.py` (pytest fixtures), `test_jobs.py`, `test_projects.py`, `test_auth.py`

**`vnc-container/`**
- Purpose: Docker image for interactive OpenROAD viewer (noVNC + X11)
- Contains: Dockerfile, supervisord.conf (process supervisor), start_session.sh (entrypoint)
- Generated from: `docker-compose build --profile build-only vnc-viewer`
- Used by: Worker container spawning (not run by compose up directly)

**`infra/nginx/`**
- Purpose: Reverse proxy configuration
- Contains: `nginx.conf` (routing rules for API, frontend, VNC)
- Used by: Nginx container in docker-compose

**`assignments/`**
- Purpose: Community-contributed ORFS lab assignments
- Contains: One directory per assignment with assignment.yaml (metadata), design/ (starter files), README.md
- Format: YAML-based assignment spec with PDK, target_stage, locked_params, checkpoint rules

## Key File Locations

**Entry Points:**

- **Backend:** `backend/app/main.py` → FastAPI app setup, imports all routers
- **Worker (ORFS jobs):** `worker/celery_app.py` → Celery app with autodiscover, `worker/celeryconfig.py` defines queue routing
- **Worker (Background):** `worker/celery_app.py` → Same Celery app, different queue filter (`-Q background`)
- **Frontend:** `frontend/src/index.tsx` → React entry point, ReactDOM.render to #root

**Configuration:**

- `backend/app/core/config.py` → All backend settings (DATABASE_URL, REDIS_URL, ORFS_IMAGE, JOB_*, etc.)
- `worker/celeryconfig.py` → Celery broker/backend URLs, task routing, beat schedule (orphaned cleanup every 2min)
- `docker-compose.yml` → Full stack setup (Postgres, Redis, MinIO, backend, workers, frontend, nginx)

**Core Logic:**

- **Job Submission:** `backend/app/api/routes/jobs.py` → POST /jobs/submit validates, creates Run, dispatches task
- **Job Execution:** `worker/tasks/orfs_job.py` → Celery task that orchestrates container lifecycle
- **Log Streaming:** `backend/app/api/websocket.py` → WS endpoint replays Redis buffer + subscribes to live channel
- **Artifact Generation:** `worker/tasks/tile_generator.py` → PNG rendering + metrics parsing + MinIO upload

**Testing:**

- `backend/tests/conftest.py` → pytest fixtures (test_db, test_redis, test_client)
- `backend/tests/test_jobs.py` → Tests for job lifecycle (submit, status, cancel)
- `backend/tests/test_projects.py` → Tests for project CRUD
- `backend/tests/test_auth.py` → Tests for login, token refresh

## Naming Conventions

**Files:**

- **Python files:** `snake_case.py` (e.g., `orfs_job.py`, `storage_service.py`, `get_current_user.py`)
- **TypeScript files:** `camelCase.ts` or `PascalCase.tsx` depending on content (e.g., `api/client.ts`, `components/LogTerminal.tsx`)
- **React components:** `PascalCase.tsx` (e.g., `FlowControlPanel.tsx`, `RunHistoryTable.tsx`)
- **Directories:** `snake_case/` for multi-word or concept dirs (e.g., `api/`, `core/`, `vnc_container/`)

**Directories:**

- **Top-level domains:** `snake_case/` (frontend, backend, worker, vnc-container, infra, assignments, scripts)
- **Feature/service dirs:** `PascalCase/` in frontend components (e.g., `FlowControlPanel/`, `LogTerminal/`)
- **Layers:** `api/`, `models/`, `schemas/`, `services/`, `core/` follow Django-style separation of concerns
- **Tasks in worker:** `snake_case.py` with @app.task decorator (e.g., `orfs_job.py`, `tile_generator.py`)

**Classes:**

- **Backend:** `PascalCase` (e.g., `ContainerManager`, `StorageService`, `MetricsService`, `Run`, `User`, `Project`)
- **Frontend:** `PascalCase` for React components (e.g., `LogTerminal`, `FlowControlPanel`)

**Functions:**

- **Backend (Python):** `snake_case` (e.g., `run_orfs_job()`, `get_current_user()`, `parse_ppa_metrics()`)
- **Frontend (TypeScript):** `camelCase` for regular functions, `PascalCase` for component functions (e.g., `submitJob()`, `cancelJob()`, `LogTerminal()`)

**Constants:**

- **Backend:** `UPPER_SNAKE_CASE` (e.g., `STAGE_PATTERNS`, `ACTIVE_STATUSES`, `LOG_BUFFER_MAX`)
- **Frontend:** `UPPER_SNAKE_CASE` for constants (e.g., `STAGES`, `ACTIVE_STATUSES`)

**Database/API:**

- **Table names:** `snake_case` (users, projects, runs, vnc_sessions)
- **Column names:** `snake_case` (user_id, created_at, stage_completed, ppa, config)
- **API endpoints:** `/api/v1/{resource}/{id}/{action}` in snake_case (e.g., `/api/v1/jobs/submit`, `/api/v1/jobs/{id}`, `/api/v1/vnc/start/{runId}`)

## Where to Add New Code

**New API Endpoint:**
1. Define Pydantic schema (request/response) in `backend/app/schemas/{domain}.py`
2. Implement route handler in `backend/app/api/routes/{domain}.py` using async/await
3. If accessing DB: use `db: AsyncSession = Depends(get_db)` dependency
4. If needing Celery: import `from app.core.celery_client import celery_app` and call `celery_app.send_task(...)`
5. If needing storage: use `StorageService = Depends(get_storage_service())`

**New Celery Task:**
1. Create task file in `worker/tasks/{task_name}.py`
2. Define `@app.task(name="tasks.{task_name}.{function_name}", queue="orfs_jobs" or "background")` decorator
3. Use synchronous database access (create_engine with sync psycopg2 URL, not async)
4. Register task routing in `worker/celeryconfig.py` task_routes dict if needed
5. Call from backend via `celery_app.send_task("tasks.{task_name}.{function_name}", args=[...])`

**New Database Model:**
1. Create model file in `backend/app/models/{entity}.py`
2. Inherit from `Base`, define columns with mapped_column(), relationships with relationship()
3. Use UUID primary keys with `server_default=text("gen_random_uuid()")`
4. For JSONB columns, use `JSONBCompatible` type for PostgreSQL/SQLite compatibility
5. Create Alembic migration: `alembic revision --autogenerate -m "Add {entity} table"`

**New React Component:**
1. Create component file in `frontend/src/components/{ComponentName}/{ComponentName}.tsx`
2. Define TypeScript interface for props
3. Use Zustand hooks to access global state: `const activeRunId = useJobStore(s => s.activeRunId)`
4. Use typed API client for backend calls: `import { getJobStatus } from "api/jobs"`
5. Add tests in `frontend/src/components/{ComponentName}/{ComponentName}.test.tsx`

**New Frontend Page:**
1. Create page file in `frontend/src/pages/{PageName}.tsx`
2. Add route in `frontend/src/App.tsx` (react-router configuration)
3. Import and use components, manage page-level state with Zustand

**New Service/Utility:**
1. If backend logic: create in `backend/app/services/{service_name}.py` as class or module
2. If utility function: place in `backend/app/utils/{utility_name}.py`
3. For dependency injection: export getter function (e.g., `def get_storage_service() -> StorageService`)
4. Use in route handlers via `service = Depends(get_storage_service_getter)`

## Special Directories

**`.planning/codebase/`**
- Purpose: Architecture and conventions documentation
- Generated: By `/gsd:map-codebase` command (Claude code mapping agent)
- Committed: Yes (tracked in git)
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md (as phases progress)

**`backend/alembic/versions/`**
- Purpose: Database migration scripts (one per schema change)
- Generated: By `alembic revision --autogenerate`
- Committed: Yes (required for reproducible DB schema)
- Location: Each migration file is timestamped and numbered (e.g., `001_initial_schema.py`, `002_add_vnc_sessions.py`)

**`frontend/dist/`**
- Purpose: Built frontend artifacts (post-build)
- Generated: By `npm run build` or `yarn build` during Docker build
- Committed: No (gitignored)
- Served by: Nginx container (COPY dist/ /usr/share/nginx/html)

**`backend/.pytest_cache/`, `worker/__pycache__/`, `frontend/node_modules/`**
- Purpose: Build and dependency cache directories
- Generated: By package managers (pip, npm) and build tools (pytest)
- Committed: No (gitignored)
- Cleaned: `docker system prune` removes all Docker build cache

**`artifacts_data/` (Docker volume)**
- Purpose: Persistent storage for MinIO data (mounted on host by docker-compose)
- Generated: By MinIO container on first startup
- Committed: No (data volume, not tracked in git)
- Used by: Worker containers (download source, upload artifacts)

---

*Structure analysis: 2026-03-13*
