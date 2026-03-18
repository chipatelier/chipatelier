# Unified Configurable Storage Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Docker named volumes with bind mounts controlled by `DATA_ROOT` and `WORKSPACE_ROOT` environment variables, so deployers can direct all persistent data to any storage mount.

**Architecture:** All named volumes in `docker-compose.yml` are replaced with bind mounts referencing `${DATA_ROOT}/{service}`. Job workspaces use `${WORKSPACE_ROOT}`. A new `scripts/install.sh` creates directories with correct ownership before first run. The live deployment requires a data migration from named volumes to the new paths.

**Tech Stack:** Bash, Docker Compose v2, Docker Engine 24+

**Spec:** `docs/superpowers/specs/2026-03-18-unified-storage-design.md`

---

## Chunk 1: Config Files and Install Script

### Task 1: Update `.env.example`

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Remove `PDK_ROOT` and add `DATA_ROOT`/`WORKSPACE_ROOT`**

Open `.env.example`. Make these changes:
1. Remove the line `PDK_ROOT=/data/pdks`
2. Add a `# --- Storage paths ---` section before `# --- OpenROAD ---`:

```bash
# --- Storage paths ---
# DATA_ROOT: all persistent data (postgres, minio, artifacts, ollama, redis).
# Point this at your largest/backed-up storage mount (NAS, LVM volume, etc.).
DATA_ROOT=/opt/apps/chipatelier/data

# WORKSPACE_ROOT: scratch space for in-flight ORFS jobs. No backup needed.
# Fast local storage (NVMe/SSD) recommended. Cleared on reboot if under /tmp.
WORKSPACE_ROOT=/tmp/chipatelier_workspaces
```

Final `.env.example` OpenROAD section should read:
```bash
# --- OpenROAD ---
ORFS_IMAGE=openroad/orfs:latest
ARTIFACTS_ROOT=/data/artifacts
WARM_POOL_SIZE=4
MAX_CONCURRENT_JOBS=12
JOB_TIMEOUT_SECONDS=7200           # 2 hours max per job
```

- [ ] **Step 2: Verify the file looks correct**

```bash
grep -n 'PDK_ROOT\|DATA_ROOT\|WORKSPACE_ROOT' .env.example
```

Expected output:
```
<line>:DATA_ROOT=/opt/apps/chipatelier/data
<line>:WORKSPACE_ROOT=/tmp/chipatelier_workspaces
```
`PDK_ROOT` must not appear.

- [ ] **Step 3: Commit**

```bash
git add .env.example
git commit -m "chore: add DATA_ROOT/WORKSPACE_ROOT to .env.example, remove PDK_ROOT"
```

---

### Task 2: Update `scripts/generate-secrets.sh`

**Files:**
- Modify: `scripts/generate-secrets.sh`

The script currently emits `PDK_ROOT=/data/pdks` (line 65) and lacks `DATA_ROOT`/`WORKSPACE_ROOT`. Fix both.

- [ ] **Step 1: Remove `PDK_ROOT` line from the heredoc**

In the `# ── OpenROAD ──` section of the heredoc (around line 63–69), remove:
```bash
PDK_ROOT=/data/pdks
```

- [ ] **Step 2: Add `DATA_ROOT` and `WORKSPACE_ROOT` to the heredoc**

Add a new section just before `# ── OpenROAD ──`:

```bash
# ── Storage paths ─────────────────────────────────────────────────────────────
# Set DATA_ROOT to your preferred storage mount before running docker compose up.
# Run scripts/install.sh after setting these to create required directories.
DATA_ROOT=/opt/apps/chipatelier/data
WORKSPACE_ROOT=/tmp/chipatelier_workspaces

```

- [ ] **Step 3: Verify the script has no syntax errors**

```bash
bash -n scripts/generate-secrets.sh && echo "Syntax OK"
```

Expected: `Syntax OK`

- [ ] **Step 4: Verify output in the written .env (do NOT run the script live — it overwrites .env)**

The script writes to `.env`, not stdout. Inspect the heredoc content directly to verify the changes are correct:

```bash
grep -n 'PDK_ROOT\|DATA_ROOT\|WORKSPACE_ROOT' scripts/generate-secrets.sh
```

Expected: lines showing `DATA_ROOT=` and `WORKSPACE_ROOT=` inside the heredoc; no line containing `PDK_ROOT=`.

- [ ] **Step 5: Commit**

```bash
git add scripts/generate-secrets.sh
git commit -m "chore: add DATA_ROOT/WORKSPACE_ROOT, remove PDK_ROOT from generate-secrets.sh"
```

---

### Task 3: Create `scripts/install.sh`

**Files:**
- Create: `scripts/install.sh`

This is a new file. It reads `DATA_ROOT` and `WORKSPACE_ROOT` from `.env` using a robust parse (not `source .env` — that breaks on comments and quoted values), creates all required directories, and applies correct ownership for container UIDs.

- [ ] **Step 1: Create the file**

```bash
cat > scripts/install.sh << 'SCRIPT'
#!/usr/bin/env bash
# install.sh — Create data directories for ChipAtelier before first docker compose up.
# Usage: bash scripts/install.sh
#
# Reads DATA_ROOT and WORKSPACE_ROOT from .env in the project root.
# Creates required subdirectories and sets ownership for container users.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$ROOT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: .env not found at $ENV_FILE" >&2
  echo "  Run: cp .env.example .env  then fill in required values." >&2
  exit 1
fi

# Parse values from .env without sourcing it (safe with comments and quotes)
parse_env() {
  grep -E "^${1}=" "$ENV_FILE" | tail -1 | cut -d= -f2- | tr -d '"'"'" | xargs
}

DATA_ROOT="$(parse_env DATA_ROOT)"
WORKSPACE_ROOT="$(parse_env WORKSPACE_ROOT)"

# Validate DATA_ROOT
if [[ -z "$DATA_ROOT" ]]; then
  echo "ERROR: DATA_ROOT is not set in $ENV_FILE" >&2
  exit 1
fi
if [[ "$DATA_ROOT" != /* ]]; then
  echo "ERROR: DATA_ROOT must be an absolute path, got: $DATA_ROOT" >&2
  exit 1
fi

# Default WORKSPACE_ROOT if not set
WORKSPACE_ROOT="${WORKSPACE_ROOT:-/tmp/chipatelier_workspaces}"
if [[ "$WORKSPACE_ROOT" != /* ]]; then
  echo "ERROR: WORKSPACE_ROOT must be an absolute path, got: $WORKSPACE_ROOT" >&2
  exit 1
fi

echo "DATA_ROOT      = $DATA_ROOT"
echo "WORKSPACE_ROOT = $WORKSPACE_ROOT"
echo ""

# Create persistent data directories
mkdir -p \
  "${DATA_ROOT}/postgres" \
  "${DATA_ROOT}/redis" \
  "${DATA_ROOT}/minio" \
  "${DATA_ROOT}/ollama" \
  "${DATA_ROOT}/artifacts"

# Create workspace scratch directory
mkdir -p "${WORKSPACE_ROOT}"

# Set ownership so containers can write as their internal users:
#   postgres:16-alpine  → UID 999
#   redis:7-alpine      → UID 999
#   minio/minio         → UID 1000
#   ollama, workers     → root (no chown needed)
echo "Setting directory ownership for container users..."
chown 999:999 "${DATA_ROOT}/postgres" "${DATA_ROOT}/redis"
chown 1000:1000 "${DATA_ROOT}/minio"

echo ""
echo "✓ Directories created and ownership set."
echo ""
echo "Verify substitution before starting services:"
echo "  docker compose config | grep -A2 'volumes:'"
echo ""
echo "Then start:"
echo "  docker compose up -d"
SCRIPT
chmod +x scripts/install.sh
```

- [ ] **Step 2: Verify the script is executable and has no syntax errors**

```bash
bash -n scripts/install.sh && echo "Syntax OK"
```

Expected: `Syntax OK`

- [ ] **Step 3: Run it against the current .env (which already has DATA_ROOT)**

```bash
bash scripts/install.sh
```

Expected output:
```
DATA_ROOT      = /opt/apps/chipatelier/data
WORKSPACE_ROOT = /tmp/chipatelier_workspaces

Setting directory ownership for container users...

✓ Directories created and ownership set.
...
```

- [ ] **Step 4: Verify directories and ownership**

```bash
ls -la /opt/apps/chipatelier/data/
stat -c "%n %U:%G" /opt/apps/chipatelier/data/postgres /opt/apps/chipatelier/data/redis /opt/apps/chipatelier/data/minio
```

Expected:
```
/opt/apps/chipatelier/data/postgres 999:999   (or numeric if user doesn't exist on host)
/opt/apps/chipatelier/data/redis    999:999
/opt/apps/chipatelier/data/minio    1000:1000
```

- [ ] **Step 5: Commit**

```bash
git add scripts/install.sh
git commit -m "feat: add install.sh to create data directories with correct ownership"
```

---

## Chunk 2: Docker Compose and README

### Task 4: Update `docker-compose.yml`

**Files:**
- Modify: `docker-compose.yml`

This is the core change. Replace all named volumes with bind mounts and add Redis persistence. The `volumes:` block at the bottom is removed entirely.

- [ ] **Step 1: Update postgres volume**

Find:
```yaml
    volumes:
      - postgres_data:/var/lib/postgresql/data
```
Replace with:
```yaml
    volumes:
      - ${DATA_ROOT}/postgres:/var/lib/postgresql/data
```

- [ ] **Step 2: Update redis — add persistence command and volume**

Find the redis service block:
```yaml
  redis:
    image: redis:7-alpine
    healthcheck:
```
Replace with:
```yaml
  redis:
    image: redis:7-alpine
    command: redis-server --save 60 1 --appendonly yes
    volumes:
      - ${DATA_ROOT}/redis:/data
    healthcheck:
```

- [ ] **Step 3: Update minio volume**

Find:
```yaml
    volumes:
      - minio_data:/data
```
Replace with:
```yaml
    volumes:
      - ${DATA_ROOT}/minio:/data
```

- [ ] **Step 4: Update ollama volume**

Find:
```yaml
    volumes:
      - ollama_data:/ollama
```
Replace with:
```yaml
    volumes:
      - ${DATA_ROOT}/ollama:/ollama
```

- [ ] **Step 5: Update orfs-worker volumes**

Find (include the comment lines — they are present in the actual file):
```yaml
      - /var/run/docker.sock:/var/run/docker.sock
      - artifacts_data:/data/artifacts
      # Workspace scratch dir must be a host bind-mount (not a named volume).
      # Worker writes workspace files here; Docker API references this same HOST
      # path when mounting into ORFS job containers.
      - /tmp/chipatelier_workspaces:/tmp/chipatelier_workspaces
```
Replace with (preserve the explanatory comment):
```yaml
      - /var/run/docker.sock:/var/run/docker.sock
      - ${DATA_ROOT}/artifacts:/data/artifacts
      # Workspace scratch dir must be a host bind-mount (not a named volume).
      # Worker writes workspace files here; Docker API references this same HOST
      # path when mounting into ORFS job containers.
      - ${WORKSPACE_ROOT}:/tmp/chipatelier_workspaces
```

- [ ] **Step 6: Update background-worker volume**

Find:
```yaml
      - artifacts_data:/data/artifacts
```
Replace with:
```yaml
      - ${DATA_ROOT}/artifacts:/data/artifacts
```

- [ ] **Step 7: Update vnc-viewer volume**

Find (include the trailing inline comment — it is present in the actual file):
```yaml
      - artifacts_data:/artifacts:ro  # DEF/LEF files from ORFS job runs
```
Replace with:
```yaml
      - ${DATA_ROOT}/artifacts:/artifacts:ro  # DEF/LEF files from ORFS job runs
```

- [ ] **Step 8: Remove the top-level `volumes:` block**

Find and delete these lines at the bottom of the file:
```yaml
volumes:
  postgres_data:
  minio_data:
  artifacts_data:
  ollama_data:
```

- [ ] **Step 9: Verify compose config resolves correctly**

```bash
docker compose config | grep -E 'source:|target:' | sort | uniq
```

Expected: all `source:` values show absolute paths under `/opt/apps/chipatelier/data/` and `/tmp/chipatelier_workspaces`. No named volume references.

Also verify no syntax errors:
```bash
docker compose config > /dev/null && echo "Config OK"
```

Expected: `Config OK`

- [ ] **Step 10: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: replace named volumes with DATA_ROOT/WORKSPACE_ROOT bind mounts, add Redis persistence"
```

---

### Task 5: Update `.env` with DATA_ROOT and WORKSPACE_ROOT

**Files:**
- Modify: `.env`

The live `.env` already has `DATA_ROOT` added but should be verified against the new compose file.

- [ ] **Step 1: Verify DATA_ROOT and WORKSPACE_ROOT are present in .env**

```bash
grep -E 'DATA_ROOT|WORKSPACE_ROOT' .env
```

Expected:
```
DATA_ROOT=/opt/apps/chipatelier/data
WORKSPACE_ROOT=/tmp/chipatelier_workspaces
```

If either is missing, add them to the `# ── OpenROAD ──` section:
```bash
DATA_ROOT=/opt/apps/chipatelier/data
WORKSPACE_ROOT=/tmp/chipatelier_workspaces
```

- [ ] **Step 2: Verify no PDK_ROOT in .env**

```bash
grep 'PDK_ROOT' .env && echo "FOUND - remove it" || echo "Not present - OK"
```

Expected: `Not present - OK` (the `.env` already has PDK_ROOT replaced with a comment — verify the comment is still present and no active line exists).

- [ ] **Step 3: Final compose config check with live .env**

```bash
docker compose config | grep -E 'source:' | sort
```

All source paths should be absolute host paths.

---

### Task 6: Migrate data from named volumes and restart

This step migrates the live deployment from named volumes to the new bind mounts. **The stack must be stopped during migration.**

- [ ] **Step 1: Stop the running stack**

```bash
docker compose --profile ollama down
```

Verify all containers stopped:
```bash
docker ps --filter "name=chipatelier"
```
Expected: no output.

- [ ] **Step 2: Run install.sh to ensure directories exist with correct ownership**

```bash
bash scripts/install.sh
```

- [ ] **Step 3: Confirm named volume names**

Docker Compose generates volume names as `{project_name}_{volume_key}`. The default project name is the directory name (`chipatelier`). Verify before proceeding:

```bash
docker volume ls | grep chipatelier
```

Expected output should include:
```
local     chipatelier_postgres_data
local     chipatelier_minio_data
local     chipatelier_ollama_data
local     chipatelier_artifacts_data
```

If the prefix differs (e.g. you used `COMPOSE_PROJECT_NAME` or `-p`), substitute that prefix in all volume names in Steps 4 and 9.

- [ ] **Step 4: Migrate data from named volumes**

For each named volume, copy its data to the new bind-mount path. The `cp -a` flag preserves ownership (correct for postgres UID 999, minio UID 1000):

```bash
# Postgres
docker run --rm \
  -v chipatelier_postgres_data:/src:ro \
  -v /opt/apps/chipatelier/data/postgres:/dst \
  alpine sh -c "cp -a /src/. /dst/ && echo 'postgres: OK'"

# MinIO
docker run --rm \
  -v chipatelier_minio_data:/src:ro \
  -v /opt/apps/chipatelier/data/minio:/dst \
  alpine sh -c "cp -a /src/. /dst/ && echo 'minio: OK'"

# Ollama
docker run --rm \
  -v chipatelier_ollama_data:/src:ro \
  -v /opt/apps/chipatelier/data/ollama:/dst \
  alpine sh -c "cp -a /src/. /dst/ && echo 'ollama: OK'"

# Artifacts
docker run --rm \
  -v chipatelier_artifacts_data:/src:ro \
  -v /opt/apps/chipatelier/data/artifacts:/dst \
  alpine sh -c "cp -a /src/. /dst/ && echo 'artifacts: OK'"

# Redis had no named volume — skip
```

Each command should print `<service>: OK`.

- [ ] **Step 5: Verify migrated data**

```bash
# Postgres data directory should contain PG_VERSION and base/
ls /opt/apps/chipatelier/data/postgres/

# MinIO should contain .minio.sys and chipatelier-artifacts bucket
ls /opt/apps/chipatelier/data/minio/

# Ollama should contain blobs/ and manifests/
ls /opt/apps/chipatelier/data/ollama/
```

- [ ] **Step 6: Start the stack**

```bash
docker compose --profile ollama up -d
```

- [ ] **Step 7: Verify all services healthy**

```bash
docker compose --profile ollama ps
```

All services should show `Up` or `Up (healthy)`. Wait up to 30 seconds for health checks to pass.

- [ ] **Step 8: Verify backend is responding**

```bash
curl -s http://localhost:8000/metrics | head -5
```

Expected: HTTP 200 with metrics content.

- [ ] **Step 9: Remove old named volumes**

Only after verifying the stack is healthy:

```bash
docker volume rm \
  chipatelier_postgres_data \
  chipatelier_minio_data \
  chipatelier_ollama_data \
  chipatelier_artifacts_data
```

Expected: each volume name echoed back as confirmation of removal.

- [ ] **Step 10: Commit (nothing to commit — migration is operational, not code)**

The `.env` changes were already staged. Commit if any `.env` edits were made in Step 1:

```bash
git diff .env && git add .env && git commit -m "chore: add DATA_ROOT and WORKSPACE_ROOT to live .env"
```

---

### Task 7: Update `README.md`

**Files:**
- Modify: `README.md`

Add a "Storage Configuration" section after the existing "Quick Start" section.

- [ ] **Step 1: Add the Storage Configuration section**

Insert the following after the Quick Start section (after the "Navigate to `http://localhost:8080`" paragraph) and before the "Services" section:

```markdown
## Storage Configuration

ChipAtelier separates persistent data from ephemeral job scratch space:

| Variable | Default | Purpose |
|---|---|---|
| `DATA_ROOT` | `/opt/apps/chipatelier/data` | All persistent data: PostgreSQL, MinIO, artifacts, Ollama models, Redis |
| `WORKSPACE_ROOT` | `/tmp/chipatelier_workspaces` | Scratch space for in-flight ORFS jobs (ephemeral, no backup needed) |

**Before first `docker compose up`, create required directories:**

```bash
bash scripts/install.sh
```

This creates subdirectories under `DATA_ROOT` and sets correct ownership for container users.

**To use a different storage mount** (NAS, dedicated LVM volume, etc.), set `DATA_ROOT` in `.env` before running `install.sh`:

```bash
DATA_ROOT=/mnt/nas/chipatelier
```

**Verify variable substitution before starting:**

```bash
docker compose config | grep -E 'source:'
```

All source paths should show absolute host paths under your `DATA_ROOT`.

**Backup guidance:**
- Back up `DATA_ROOT` — it contains all durable state (database, artifacts, models)
- Skip `WORKSPACE_ROOT` — ephemeral scratch space, cleared on reboot

**Migrating from a previous installation** (named volumes → bind mounts): see `docs/superpowers/specs/2026-03-18-unified-storage-design.md` for step-by-step migration instructions.
```

- [ ] **Step 2: Verify the section renders correctly**

```bash
grep -A 40 '## Storage Configuration' README.md
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add Storage Configuration section to README"
```

---

## Verification

After all tasks are complete, run a full end-to-end check:

- [ ] **All containers healthy**

```bash
docker compose --profile ollama ps
```

Expected: all services `Up` or `Up (healthy)`.

- [ ] **Data is persisted to DATA_ROOT**

```bash
du -sh /opt/apps/chipatelier/data/*/
```

Expected: non-zero sizes for postgres, minio, ollama (artifacts may be small if no jobs have run).

- [ ] **No named volumes remain**

```bash
docker volume ls | grep chipatelier
```

Expected: no output (all chipatelier named volumes removed).

- [ ] **generate-secrets.sh heredoc contains correct variables**

```bash
grep -E 'DATA_ROOT|WORKSPACE_ROOT|PDK_ROOT' scripts/generate-secrets.sh
```

Expected: lines showing `DATA_ROOT=` and `WORKSPACE_ROOT=` inside the heredoc; `PDK_ROOT` absent.
