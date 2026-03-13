# Technology Stack

**Analysis Date:** 2025-03-13

## Languages

**Primary:**
- Python 3.12 - Backend (FastAPI), worker tasks (Celery), CLI tooling
- TypeScript 5.6 - Frontend application (React 18)

**Secondary:**
- JavaScript (ES2022) - Frontend bundling and module federation via Vite

## Runtime

**Environment:**
- Python 3.12-slim (Docker base image for backend and worker)
- Node.js (implied by Vite/React build; pinned via package-lock.json)
- Docker daemon with socket mount to worker containers (host-mounted `/var/run/docker.sock`)

**Package Managers:**
- Python: `uv` (configured in both backend and worker Dockerfiles)
  - Lockfile: Not committed; dependencies managed via `pyproject.toml`
- Node.js: npm
  - Lockfile: `package-lock.json` present and committed

## Frameworks

**Core Backend:**
- FastAPI 0.115.x - REST API server, async request handling, OpenAPI docs at `/docs`
- Uvicorn 0.32.x - ASGI server (uvicorn app.main:app --host 0.0.0.0 --port 8000)

**Job Queue & Task Execution:**
- Celery 5.4.x - Distributed task queue for ORFS job execution and background work
- Redis 7.x - Broker, results backend, pubsub for log streaming
- redis-py 5.x (asyncio variant) - Async Redis client in backend, sync in worker

**Database:**
- SQLAlchemy 2.0.x (async support) - ORM for PostgreSQL
- asyncpg 0.29.x - PostgreSQL async driver for backend
- Alembic 1.13.x - Database migrations (schema managed in `/alembic`)
- pydantic 2.x - Data validation schemas
- pydantic-settings 2.x - Environment-based configuration

**Frontend Build & Testing:**
- Vite 5.4.x - Dev server (proxy to :8000/api), production bundler
- React 18.3.x - Component framework
- React Router 7.13.x - Client-side routing
- TypeScript 5.6.x - Static typing
- Vitest 2.x - Unit/component test runner
- Testing Library - React component testing utilities

**Frontend State & Data:**
- Zustand 5.x - Lightweight state management (no boilerplate)
- Axios 1.7.x - HTTP client (typed via backend OpenAPI schemas)
- xterm.js 5.5.x + addons - Terminal emulation for log viewing
  - Includes @xterm/addon-fit, @xterm/addon-search, @xterm/addon-attach

**Code Quality:**
- ESLint 9.x - Frontend linting (TypeScript + React rules)
- Prettier 3.x - Code formatting (enforced via `npm run format`)
- ruff - Python linter/formatter (config in backend/pyproject.toml)
- mypy - Static type checking for Python (strict mode in backend/pyproject.toml)
- pytest 8.x - Python test runner (backend)
- pytest-asyncio 0.24.x - Async test support

**Container Runtime:**
- Docker SDK for Python 7.1.x - Container lifecycle management in worker tasks
- Docker Compose 3.x - Full-stack orchestration

## Key Dependencies

**Critical Infrastructure:**
- docker 7.1.x - Docker SDK for Python; controls ORFS job containers and VNC containers (`worker/container/manager.py`)
- boto3 1.35.x - S3/MinIO client for artifact upload/download; uses S3v4 signature required for MinIO compatibility (`backend/app/services/storage_service.py`)
- sqlalchemy[asyncio] 2.0.x - Async database access; critical for concurrent job status tracking

**Authentication & Security:**
- PyJWT 2.10.x - JWT token encoding/decoding for API access tokens and VNC session tokens
- argon2-cffi 25.x - Password hashing (Argon2id, memory-hard)

**Supporting Libraries:**
- httpx 0.27.x - Async HTTP client for backend-to-worker communication and external service calls
- aiofiles 24.x - Async file I/O for artifact handling
- python-multipart 0.0.12 - File upload parsing (FastAPI multipart/form-data)

**Testing & Mocking:**
- moto[s3] - Mock S3/MinIO for integration tests (backend tests)
- fakeredis - In-memory Redis for unit tests (no network required)
- aiosqlite - SQLite async driver for test database isolation

## Configuration

**Environment Configuration:**
- `.env` file (copied from `.env.example`, never committed)
- Sourced via pydantic-settings `Settings` class in `backend/app/core/config.py`
- All secrets (database credentials, API keys, JWT secrets) passed as env vars

**Key Configurable Settings:**
- `DATABASE_URL`: PostgreSQL connection string (asyncpg driver)
- `REDIS_URL`: Redis broker connection string
- `STORAGE_BACKEND`: "minio" (local) or "s3" (cloud)
- `ORFS_IMAGE`: Docker image tag for ORFS container jobs (locked to prevent mid-semester breakage)
- `JOB_CPU_CORES`, `JOB_RAM_GB`, `JOB_DISK_GB`: Per-job resource limits enforced via Docker cgroup
- `ORFS_WORKER_CONCURRENCY`: Dedicated ORFS job worker concurrency (4 default)
- `BACKGROUND_WORKER_CONCURRENCY`: Dedicated background worker concurrency (2 default)
- `LLM_BACKEND`: "ollama" (local) or "anthropic"/"openai" (cloud)

**Build Configuration:**
- `backend/pyproject.toml`: Python project metadata, dependencies, build backend (hatchling)
- `frontend/tsconfig.json`: TypeScript strict mode, React JSX transform, module resolution
- `frontend/vite.config.ts`: Vite dev server proxy to :8000/api, jsdom test environment
- Docker Compose volumes: `postgres_data`, `minio_data`, `artifacts_data` (persistent)

## Platform Requirements

**Development:**
- Python 3.12+ (backend)
- Node.js 18+ (frontend, implied by Vite)
- Docker daemon (for local ORFS container testing)
- Docker Compose v2+

**Production/Deployment:**
- Docker Compose v2+ (official deployment method)
- PostgreSQL 16 (database service)
- Redis 7 (broker + pubsub)
- MinIO or S3-compatible storage
- Single server or Kubernetes (future; Helm chart in `/infra/kubernetes`)

**Deployment Target:**
- On-premise university server (Docker Compose default)
- Can scale horizontally with separate worker hosts (Docker socket mount on each)
- Tested on DL380 Gen9 (dual E5-2600 CPUs, 28-36 cores total) — resource profile documented in CLAUDE.md

**ORFS Container Requirements:**
- Docker image: `openroad/orfs:latest` (or pinned version)
- Base: Fedora/CentOS with OpenROAD, KLayout, and ORFS flow scripts pre-installed
- No network access (containers spawn with `network_mode="none"`)
- Read-only filesystem except /tmp (enforced in `worker/container/manager.py`)
- Runs as unprivileged user "orfs:orfs" inside container

---

*Stack analysis: 2025-03-13*
