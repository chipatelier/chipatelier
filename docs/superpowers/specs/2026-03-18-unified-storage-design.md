# Unified Configurable Storage Design

**Date:** 2026-03-18
**Status:** Approved

## Problem

ChipAtelier's persistent data is currently spread across Docker named volumes (stored implicitly under `/var/lib/docker/volumes/`) and a hardcoded bind-mount at `/tmp/chipatelier_workspaces`. Deployers cannot redirect data to a different storage mount (NAS, dedicated LVM volume, external disk) without manually editing `docker-compose.yml`. This is a barrier for university deployments where large storage is on a separate mount from the OS.

## Goals

- All persistent data (postgres, minio, artifacts, ollama, redis) configurable via a single `DATA_ROOT` environment variable.
- Job workspace scratch space configurable separately via `WORKSPACE_ROOT` — different storage characteristics (fast, ephemeral, no backup needed).
- No change to application code — only Docker Compose, `.env`, and documentation.
- Sensible defaults that work out of the box without configuration.

## Out of Scope

- Moving Docker image layers or build cache (always in `/var/lib/docker`).
- Per-service storage path overrides (one `DATA_ROOT` covers all persistent services).
- Kubernetes or non-Docker-Compose deployment targets.

## Design

### New Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `DATA_ROOT` | `/opt/apps/chipatelier/data` | Root for all persistent data — postgres, minio, artifacts, ollama, redis |
| `WORKSPACE_ROOT` | `/tmp/chipatelier_workspaces` | Scratch space for in-flight ORFS job containers |

`DATA_ROOT` defaults to `/opt/apps/chipatelier/data`, placing it on the 2.5 TB `/opt/apps` LVM volume on the reference server. Deployers on other servers set this to their preferred mount.

`WORKSPACE_ROOT` defaults to `/tmp/chipatelier_workspaces`, on the dedicated 50 GB `/tmp` partition. It is intentionally separate from `DATA_ROOT` because it is ephemeral (cleared on reboot, no backup required) and benefits from fast local storage.

### Directory Structure Under DATA_ROOT

```
$DATA_ROOT/
  postgres/       ← PostgreSQL 16 data directory
  redis/          ← Redis 7 AOF/RDB persistence
  minio/          ← MinIO object storage (artifacts, ODB, GDS, PNGs)
  ollama/         ← Ollama model files
  artifacts/      ← ORFS job artifacts (shared by orfs-worker + background-worker)
```

### Docker Compose Changes

All named volumes for persistent services are replaced with bind mounts referencing `DATA_ROOT`. The top-level `volumes:` block is removed entirely.

**postgres:**
```yaml
volumes:
  - ${DATA_ROOT}/postgres:/var/lib/postgresql/data
```

**redis:**
```yaml
volumes:
  - ${DATA_ROOT}/redis:/data
```

**minio:**
```yaml
volumes:
  - ${DATA_ROOT}/minio:/data
```

**ollama:**
```yaml
volumes:
  - ${DATA_ROOT}/ollama:/ollama
```

**orfs-worker:**
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
  - ${DATA_ROOT}/artifacts:/data/artifacts
  - ${WORKSPACE_ROOT}:/tmp/chipatelier_workspaces
```

**background-worker:**
```yaml
volumes:
  - ${DATA_ROOT}/artifacts:/data/artifacts
```

### Pre-Start Directory Creation

Bind mounts require host directories to exist before `docker compose up`. `scripts/install.sh` creates them:

```bash
source .env
mkdir -p "${DATA_ROOT}/postgres"
mkdir -p "${DATA_ROOT}/redis"
mkdir -p "${DATA_ROOT}/minio"
mkdir -p "${DATA_ROOT}/ollama"
mkdir -p "${DATA_ROOT}/artifacts"
mkdir -p "${WORKSPACE_ROOT}"
```

### Files Changed

| File | Change |
|---|---|
| `docker-compose.yml` | Replace named volumes with bind mounts; remove `volumes:` block |
| `.env` | Add `DATA_ROOT` and `WORKSPACE_ROOT` |
| `.env.example` | Add `DATA_ROOT` and `WORKSPACE_ROOT` with inline docs; remove `PDK_ROOT` |
| `scripts/install.sh` | Add `mkdir -p` for all data subdirectories |
| `README.md` | Add "Storage Configuration" section |

### README Storage Configuration Section

Documents:
- Purpose of `DATA_ROOT` and `WORKSPACE_ROOT`
- How to point `DATA_ROOT` at a different mount (NAS, LVM volume)
- The `mkdir -p` prerequisite before first `docker compose up`
- Backup guidance: back up `DATA_ROOT`; skip `WORKSPACE_ROOT`

## Migration for Existing Deployments

Existing deployments using named volumes must migrate data before switching to bind mounts. Migration steps (to be documented in README):

1. Stop the stack: `docker compose down`
2. Set `DATA_ROOT` in `.env`
3. Create directories: run `scripts/install.sh` or `mkdir -p` manually
4. Copy data out of named volumes into the new paths:
   ```bash
   docker run --rm \
     -v chipatelier_postgres_data:/src:ro \
     -v ${DATA_ROOT}/postgres:/dst \
     alpine sh -c "cp -a /src/. /dst/"
   # Repeat for minio, redis, ollama, artifacts
   ```
5. Start the stack: `docker compose up -d`
6. Verify services healthy, then remove old named volumes: `docker volume rm chipatelier_postgres_data ...`

## Backup Guidance

- **Back up `DATA_ROOT`:** Contains all durable state. Use rsync, restic, or filesystem snapshots.
- **Skip `WORKSPACE_ROOT`:** Ephemeral scratch — no backup value. In-flight jobs lose their workspace on reboot, which is acceptable since jobs can be requeued.
