#!/usr/bin/env bash
# install.sh — Create data directories for ChipAtelier before first docker compose up.
# Usage: sudo bash scripts/install.sh
#
# Must be run as root (or with sudo) — chown requires root to set container UIDs.
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

if [[ "$EUID" -ne 0 ]]; then
  echo "WARNING: Not running as root. chown steps will fail." >&2
  echo "  Re-run as: sudo bash scripts/install.sh" >&2
  echo ""
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
