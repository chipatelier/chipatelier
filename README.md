# ChipAtelier

Browser-based RTL-to-GDS ASIC learning platform for universities — no local EDA tools required.

## What it is

ChipAtelier gives university students a fully managed RTL-to-GDS ASIC implementation environment.
Students submit Verilog designs through a browser portal, run the full OpenROAD flow (synthesis
through routing), view live logs, inspect layouts, and receive AI-assisted feedback — all on shared
university hardware without installing any EDA tools locally. Powered by OpenROAD Flow Scripts (ORFS).
Apache 2.0.

## Prerequisites

- Docker Engine 24+ and Docker Compose v2
- 16+ GB RAM, 8+ CPU cores (28-36 cores recommended for 30-40 concurrent students)
- SKY130 PDK files (see [PDK Setup](#pdk-setup) below)
- Git

## Quick Start (5 minutes)

**1. Clone the repository**

```bash
git clone https://github.com/chipatelier/chipatelier && cd chipatelier
```

**2. Configure environment**

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```bash
JWT_SECRET_KEY=<long-random-string>        # MUST change — auth token signing key
VNC_TOKEN_SECRET=<long-random-string>      # MUST change — VNC session token key
POSTGRES_PASSWORD=<strong-password>        # MUST change — database password
PDK_ROOT=/data/pdks                        # path to your PDK directory on the host
```

Generate random secrets with: `openssl rand -hex 32`

**3. Set up PDK**

```bash
# Point PDK_ROOT in .env to a directory containing sky130A (from google/skywater-pdk or open-pdks)
# Example structure expected:
#   /data/pdks/sky130A/
PDK_ROOT=/data/pdks
```

**4. Start all services**

```bash
docker compose up -d
```

This builds all images on first run. Subsequent starts are fast.

**5. Open the portal**

Navigate to `http://localhost:8080` in your browser.

Default admin account: `admin@example.com` / `changeme` — **change this immediately** in the admin panel.

## Services

| Service | Port | Purpose |
|---|---|---|
| Nginx (reverse proxy) | 8080 | Frontend + API routing, VNC session proxying |
| Frontend (React) | — (internal) | Student and instructor portal |
| Backend API (FastAPI) | 8000 | REST API + WebSocket log streaming |
| PostgreSQL 16 | 5432 | Metadata, metrics, users, courses |
| Redis 7 | 6379 | Job queue (Celery broker) + log pubsub |
| MinIO | 9001 (console) | Artifact storage (ODB, GDS, logs, PNGs) |
| orfs-worker (Celery) | — | ORFS job execution (high_priority + orfs_jobs queues) |
| background-worker (Celery) | — | Tile generation, grading, AI hints (background queue) |
| VNC viewer | 6080-6099 | noVNC sessions to OpenROAD Qt GUI (dynamically spawned) |

Ollama (AI inference) runs as a separate service on the host. Set `OLLAMA_BASE_URL` in `.env`.

## PDK Setup

SKY130 is the only supported PDK for MVP. Download SKY130A from:

- [google/skywater-pdk](https://github.com/google/skywater-pdk) + open-pdks
- or via the [IIC-OSIC-TOOLS](https://github.com/iic-jku/iic-osic-tools) bundled PDKs

Set `PDK_ROOT` in `.env` to the parent directory containing `sky130A/`. The ORFS containers
mount this directory read-only at `/pdks`.

GF180 and ASAP7 support is planned for Phase 2 with no architectural changes required.

## Environment Variables

See `.env.example` for the full list with descriptions. The variables that **must** be changed
before any production deployment:

| Variable | Why |
|---|---|
| `JWT_SECRET_KEY` | Signs all access tokens — if leaked, anyone can forge auth |
| `VNC_TOKEN_SECRET` | Signs VNC session tokens — scoped separately from main JWT |
| `POSTGRES_PASSWORD` | Database password — default `changeme` is not safe |

Other key tuning variables for your server's capacity:

| Variable | Default | Description |
|---|---|---|
| `MAX_CONCURRENT_JOBS` | 12 | Max parallel ORFS jobs |
| `JOB_CPU_CORES` | 6 | CPU cores per job container |
| `JOB_RAM_GB` | 8 | RAM per job container |
| `MAX_VNC_SESSIONS` | 8 | Max simultaneous VNC viewers |
| `ORFS_WORKER_CONCURRENCY` | 4 | ORFS Celery worker concurrency |

## Resource Sizing

A single server with dual Xeon E5-2600 (28-36 total cores) can support approximately 4-6
concurrent ORFS jobs at 6 cores each. At 30-40 students with typical staggered usage,
this is usually sufficient with fair queuing.

For larger cohorts or heavier usage, an AMD EPYC or Intel Xeon Scalable platform is recommended.

Key tuning knobs: `JOB_CPU_CORES`, `JOB_RAM_GB`, `MAX_CONCURRENT_JOBS`, `MAX_VNC_SESSIONS`,
`ORFS_WORKER_CONCURRENCY`.

## Architecture

React + TypeScript frontend → FastAPI backend (REST + WebSocket) → Celery workers →
OpenROAD Docker containers (one per job, isolated, no network). Storage: PostgreSQL 16
(metadata + metrics JSONB), Redis 7 (queue + pubsub), MinIO (artifacts). Interactive layout
viewer via noVNC → OpenROAD Qt GUI.

See [CLAUDE.md](./CLAUDE.md) for full architecture details, database schema, and API reference.

## Updates

```bash
git pull
docker compose build
docker compose up -d
```

Database migrations run automatically on backend startup via Alembic.

## License

Apache 2.0 — see [LICENSE](./LICENSE).

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).
