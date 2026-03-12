# Stack Research

**Domain:** Web-based ASIC/EDA education platform (RTL-to-GDS job orchestration, live log streaming, layout visualization, AI assistance)
**Researched:** 2026-03-12
**Confidence:** HIGH — all pre-decided choices in CLAUDE.md validated; versions verified from installed packages on host

## Recommended Stack

### Core Technologies (Pre-decided — validated)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| FastAPI | 0.117.x | REST API + WebSocket backend | Async-native, excellent OpenAPI spec generation, native Pydantic integration; OpenROAD Python API access in same process |
| Celery | 5.5.x | Distributed job queue | Mature, ORFS job orchestration, Redis broker for pub/sub log streaming, fair queuing |
| Redis | 7.x | Celery broker + pub/sub log streaming | Sub-millisecond pub/sub for live logs; Celery broker; job heartbeat store |
| PostgreSQL | 16.x | Primary database | JSONB for metrics/config (GIN-indexed), pgvector future option, mature async support via asyncpg |
| MinIO | RELEASE.2025+ | Artifact storage (S3-compatible) | Same boto3/aioboto3 code works with S3; no vendor lock-in; local-first for on-prem |
| React + TypeScript | 19.x + 5.x | Frontend | Strict mode TypeScript; component ecosystem for complex UI; MapLibre GL integrations |
| MapLibre GL | 5.20.0 | Tiled layout viewer | Open-source Mapbox fork; tiled raster + vector layers; client-side layer compositing |
| noVNC | 1.6.0 (`@novnc/novnc`) | VNC viewer in browser | Proven WebSocket-to-VNC bridge; no plugin required; OpenROAD Qt GUI at full fidelity |
| Zustand | 5.0.11 | Frontend state management | Lightweight; no boilerplate vs Redux; excellent TypeScript inference |
| Ollama | latest | Local LLM inference | Design data stays on-prem; pluggable model swap; reasonable latency on GPU server |
| Docker | 27.x | Container runtime (worker host) | Socket mount simpler than DinD; per-job isolation; ORFS image management |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| SQLAlchemy | 2.0.43 | ORM + async DB sessions | All DB access via async sessions; never use sync SQLAlchemy in FastAPI |
| asyncpg | 0.30.x | PostgreSQL async driver | Required for SQLAlchemy async with PostgreSQL |
| Alembic | 1.16.5 | Database migrations | All schema changes; never edit tables manually |
| Pydantic | 2.11.9 | Schema validation + settings | API request/response schemas; `pydantic-settings` for config |
| PyJWT | 2.10.x | JWT token signing/verification | Access tokens (15min) + VNC tokens (2hr); **use this, not python-jose** |
| argon2-cffi | 25.x | Password hashing | Argon2id algorithm; **use this directly, not passlib** |
| aioboto3 | 13.x | Async S3/MinIO client | All artifact reads/writes in async FastAPI endpoints |
| redis-py | 6.4.0 | Redis client (async) | Log streaming pub/sub; Celery result backend |
| xterm.js | 6.0.0 (`@xterm/xterm`) | Terminal emulator in browser | Live log streaming with ANSI color; WebSocket source |
| TanStack Query | 5.x | Client-side server state | Job status polling, project/run lists — replaces manual useEffect fetching |
| openapi-typescript + openapi-fetch | latest | Type-safe API client | Generate TypeScript client from FastAPI OpenAPI spec; end-to-end type safety |
| Radix UI | latest | Accessible headless components | Dialog, Select, Tabs, Tooltip — unstyled, fully accessible |
| react-router-dom | 7.x | Client-side routing | Page navigation; nested routes for project/run views |
| KLayout Python API | 0.29.x | Layout tile generation (server) | GDS/DEF → PNG tiles; runs in Celery background worker |
| supervisord | 4.x | VNC container process management | Manages Xvfb + x11vnc + websockify in VNC container |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Python package management + venv | Replaces pip/poetry; significantly faster; lockfile-based |
| ruff | Python linting + formatting | Replaces flake8 + black + isort; single tool |
| mypy | Python type checking | Strict mode; catch type errors before runtime |
| Vite | Frontend build + dev server | 8.0.0; HMR; fast; native TypeScript |
| ESLint + Prettier | TypeScript linting + formatting | Strict config; consistent style |
| pytest + pytest-asyncio | Backend testing | Async test support; target 80% coverage |
| Vitest | Frontend testing | Native Vite integration; fast |
| Flower | Celery monitoring | Web UI for queue inspection; critical for debugging stuck jobs |

## Installation

```bash
# Python backend (uv)
uv add fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic \
       pydantic pydantic-settings PyJWT argon2-cffi aioboto3 redis \
       celery[redis] flower

# Dev dependencies
uv add --dev ruff mypy pytest pytest-asyncio httpx

# Frontend (npm)
npm install react react-dom react-router-dom zustand \
            maplibre-gl @novnc/novnc @xterm/xterm \
            @tanstack/react-query openapi-fetch \
            @radix-ui/react-dialog @radix-ui/react-select @radix-ui/react-tabs \
            tailwindcss

npm install -D typescript vite @vitejs/plugin-react eslint prettier \
               openapi-typescript vitest
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Celery + Redis | Dramatiq | Simpler apps without Redis pub/sub requirement; no equivalent to log streaming |
| PostgreSQL 16 | MySQL 8 | MySQL is fine; PostgreSQL chosen for JSONB GIN indexes and pgvector future option |
| MinIO | Local filesystem | Single-node dev only; MinIO gives S3 API compatibility from day 1 |
| MapLibre GL | OpenLayers | OpenLayers has more GIS features but heavier; MapLibre GL sufficient for tile compositing |
| noVNC | Guacamole | Guacamole adds Java servlet complexity; noVNC is purpose-built for WebSocket VNC |
| Zustand | Redux Toolkit | Redux for larger teams needing strict patterns; Zustand cleaner for this app size |
| Ollama | vLLM | vLLM requires CUDA + more GPU VRAM; Ollama runs on CPU too, easier to deploy |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `python-jose` | Unmaintained since 2022; open CVEs; abandoned | `PyJWT 2.10.x` |
| `passlib` | Maintenance-only mode since 2020; no active development | `argon2-cffi 25.x` directly |
| Synchronous SQLAlchemy in FastAPI | Blocks event loop; kills async performance under concurrent jobs | SQLAlchemy 2.0 async sessions |
| All-in-one Celery queue | Background tasks starved when ORFS workers busy | Dedicated `orfs_jobs` + `background` queues |
| Celery `task_always_eager` in tests | Hides real queue behavior; masks timing/serialization bugs | Use test Redis or mock at service layer |
| `boto3` (sync) in FastAPI routes | Blocks event loop during artifact reads/writes | `aioboto3` |

## Stack Patterns by Variant

**If deploying to cloud (AWS/GCP):**
- Switch `STORAGE_BACKEND=s3` in `.env` — no code changes needed
- Same `aioboto3` code, different endpoint

**If using cloud LLM instead of Ollama:**
- Set `LLM_BACKEND=anthropic` or `openai` in `.env`
- `llm_client.py` already designed as pluggable adapter

**If scaling beyond single server:**
- Celery workers can be distributed — Redis broker is already network-accessible
- MinIO supports multi-node; switch to S3 for full managed storage

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| SQLAlchemy 2.0.43 | asyncpg 0.30.x | Async engine requires asyncpg; do not use psycopg2 with async |
| Celery 5.5.x | Redis 7.x | Fully compatible; use `redis://` URL |
| Pydantic 2.11.x | FastAPI 0.117.x | Pydantic v2 only; do not mix v1 models |
| MapLibre GL 5.20.0 | React 19.x | Use `maplibre-gl` directly, not react-map-gl wrapper (adds dependency) |
| `@xterm/xterm` 6.0.0 | React 19.x | Use imperative API via useRef; not a React-wrapped component |

## Sources

- System package verification (`pip show`, `npm list`) — versions confirmed on host
- CLAUDE.md architectural decisions — validated all pre-decided choices
- CVE/maintenance status — python-jose, passlib flags from known community reports

---
*Stack research for: Web-based ASIC education platform (ChipAtelier)*
*Researched: 2026-03-12*
