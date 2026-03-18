# Unified Configurable Storage Design

**Date:** 2026-03-18
**Status:** Approved

## Problem

ChipAtelier's persistent data is currently spread across Docker named volumes (stored implicitly under `/var/lib/docker/volumes/`) and a hardcoded bind-mount at `/tmp/chipatelier_workspaces`. Deployers cannot redirect data to a different storage mount (NAS, dedicated LVM volume, external disk) without manually editing `docker-compose.yml`. This is a barrier for university deployments where large storage is on a separate mount from the OS.

## Goals

- All persistent data (postgres, minio, artifacts, ollama, redis) configurable via a single `DATA_ROOT` environment variable.
- Job workspace scratch space configurable separately via `WORKSPACE_ROOT` — different storage characteristics (fast, ephemeral, no backup needed).
- No change to application code — only Docker Compose, env files, scripts, and documentation.
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

**Important:** `WORKSPACE_ROOT` is the host-side path only. The container-side mount destination is always `/tmp/chipatelier_workspaces` and must not be changed — application code in `worker/tasks/orfs_job.py` hardcodes this container-side path.

Similarly, `ARTIFACTS_ROOT` in `.env` is the container-internal path (`/data/artifacts`) and must not be changed to match `DATA_ROOT`. The bind mount `${DATA_ROOT}/artifacts:/data/artifacts` bridges the two — `DATA_ROOT` controls the host side; `ARTIFACTS_ROOT` always stays `/data/artifacts` inside the container.

**Validation:** If `DATA_ROOT` is missing from `.env`, Docker Compose will produce a broken anonymous volume mount. Run `docker compose config` before `docker compose up` to verify variable substitution. `scripts/install.sh` must validate that `DATA_ROOT` is non-empty before creating directories.

### Directory Structure Under DATA_ROOT

```
$DATA_ROOT/
  postgres/       ← PostgreSQL 16 data directory
  redis/          ← Redis 7 AOF/RDB persistence (see Redis note below)
  minio/          ← MinIO internal object storage layout
  ollama/         ← Ollama model files
  artifacts/      ← Local filesystem artifacts used by orfs-worker and background-worker
                    (distinct from minio/ — workers write here via ARTIFACTS_ROOT,
                     MinIO stores its own object layout in minio/)
```

### Redis Persistence Note

The current `docker-compose.yml` has no volume for Redis — Redis is running without AOF/RDB persistence. This change adds persistence by mounting `${DATA_ROOT}/redis:/data`. However, mounting `/data` alone does not activate persistence; the Redis container must also be configured to write to that path.

Add `--save 60 1 --appendonly yes` to the Redis command in `docker-compose.yml`:
```yaml
redis:
  image: redis:7-alpine
  command: redis-server --save 60 1 --appendonly yes
  volumes:
    - ${DATA_ROOT}/redis:/data
```

This is a behavioural change (Redis goes from ephemeral to persistent) in addition to a path change. Deployments that relied on Redis being ephemeral (e.g. intentionally clearing queue state on restart) should be aware of this.

### Docker Compose Changes

All named volumes for persistent services are replaced with bind mounts. The top-level `volumes:` block is removed entirely.

**postgres:**
```yaml
volumes:
  - ${DATA_ROOT}/postgres:/var/lib/postgresql/data
```

**redis:**
```yaml
command: redis-server --save 60 1 --appendonly yes
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

**vnc-viewer:**
```yaml
volumes:
  - ${DATA_ROOT}/artifacts:/artifacts:ro
```

### Directory Ownership Requirements

Bind mounts on Linux inherit the host directory's ownership. Services run as non-root users inside their containers and will fail silently if the host directory is owned by root.

| Directory | Container UID | Required host ownership |
|---|---|---|
| `${DATA_ROOT}/postgres` | 999 (postgres) | `chown 999:999` |
| `${DATA_ROOT}/redis` | 999 (redis) | `chown 999:999` |
| `${DATA_ROOT}/minio` | 1000 (minio) | `chown 1000:1000` |
| `${DATA_ROOT}/ollama` | 0 (root) | No chown needed |
| `${DATA_ROOT}/artifacts` | 0 (root) | No chown needed |
| `${WORKSPACE_ROOT}` | 0 (root) | No chown needed |

`scripts/install.sh` must apply these `chown` calls after creating the directories.

**Migration exception:** When migrating from named volumes using `cp -a`, ownership is preserved from the named volume — the `chown` step is skipped for migrated directories. Only fresh installs need `chown`.

### Pre-Start Directory Creation (`scripts/install.sh` — new file)

`scripts/install.sh` does not currently exist and must be created. It sources `DATA_ROOT` and `WORKSPACE_ROOT` directly from the `.env` file using a robust parse (not `source .env`, which is fragile with comments and quoted values):

```bash
#!/usr/bin/env bash
set -euo pipefail

# Parse DATA_ROOT and WORKSPACE_ROOT from .env without sourcing it
DATA_ROOT=$(grep -E '^DATA_ROOT=' .env | cut -d= -f2- | tr -d '"'"'" | xargs)
WORKSPACE_ROOT=$(grep -E '^WORKSPACE_ROOT=' .env | cut -d= -f2- | tr -d '"'"'" | xargs)

if [[ -z "$DATA_ROOT" ]]; then
  echo "ERROR: DATA_ROOT is not set in .env" >&2
  exit 1
fi

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/tmp/chipatelier_workspaces}"

mkdir -p "${DATA_ROOT}/postgres" "${DATA_ROOT}/redis" "${DATA_ROOT}/minio" \
         "${DATA_ROOT}/ollama" "${DATA_ROOT}/artifacts"
mkdir -p "${WORKSPACE_ROOT}"

# Set ownership so containers can write as their internal users
chown 999:999 "${DATA_ROOT}/postgres" "${DATA_ROOT}/redis"
chown 1000:1000 "${DATA_ROOT}/minio"
```

### Files Changed

| File | Change |
|---|---|
| `docker-compose.yml` | Replace named volumes with bind mounts; add Redis persistence command; remove `volumes:` block |
| `.env` | Add `DATA_ROOT` and `WORKSPACE_ROOT` |
| `.env.example` | Add `DATA_ROOT` and `WORKSPACE_ROOT` with inline docs; remove `PDK_ROOT` |
| `scripts/install.sh` | **New file** — creates data directories, applies ownership |
| `scripts/generate-secrets.sh` | Add `DATA_ROOT` and `WORKSPACE_ROOT` output; remove `PDK_ROOT` output (currently still emits `PDK_ROOT=/data/pdks`) |
| `README.md` | Add "Storage Configuration" section |

### README Storage Configuration Section

Documents:
- Purpose of `DATA_ROOT` and `WORKSPACE_ROOT`
- How to point `DATA_ROOT` at a different mount (NAS, LVM volume)
- Running `scripts/install.sh` before first `docker compose up`
- Verifying variable substitution with `docker compose config`
- Backup guidance: back up `DATA_ROOT`; skip `WORKSPACE_ROOT`

## Migration for Existing Deployments

Existing deployments using named volumes must migrate data before switching to bind mounts.

> **Note:** Docker Compose generates volume names as `{project_name}_{volume_key}`. The default project name is the directory name (`chipatelier`). If you used a custom project name (via `COMPOSE_PROJECT_NAME` or `-p`), replace `chipatelier_` in the volume names below with your actual prefix. Run `docker volume ls` to confirm.

Migration steps:

1. Stop the stack: `docker compose down`
2. Set `DATA_ROOT` and `WORKSPACE_ROOT` in `.env`
3. Run `scripts/install.sh` to create directories (skip `chown` for migrated dirs — ownership is preserved by `cp -a`)
4. Copy data out of named volumes:
   ```bash
   for svc in postgres minio ollama artifacts; do
     docker run --rm \
       -v chipatelier_${svc}_data:/src:ro \
       -v ${DATA_ROOT}/${svc}:/dst \
       alpine sh -c "cp -a /src/. /dst/"
   done
   # Redis had no named volume — skip
   ```
5. Start the stack: `docker compose up -d`
6. Verify all services are healthy: `docker compose ps`
7. Remove old named volumes:
   ```bash
   docker volume rm chipatelier_postgres_data chipatelier_minio_data \
     chipatelier_ollama_data chipatelier_artifacts_data
   ```

## Backup Guidance

- **Back up `DATA_ROOT`:** Contains all durable state. Use rsync, restic, or filesystem snapshots. The `/backup` LVM volume (150 GB, nearly empty) on the reference server is a natural target.
- **Skip `WORKSPACE_ROOT`:** Ephemeral scratch — no backup value. In-flight jobs lose their workspace on reboot, which is acceptable since jobs can be requeued.
