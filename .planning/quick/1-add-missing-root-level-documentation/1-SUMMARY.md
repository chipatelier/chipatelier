---
phase: quick
plan: 1
subsystem: documentation
tags: [docs, readme, license, contributing, open-source]
dependency_graph:
  requires: []
  provides: [root-docs]
  affects: []
tech_stack:
  added: []
  patterns: []
key_files:
  created:
    - README.md
    - LICENSE
    - CONTRIBUTING.md
  modified: []
decisions:
  - "README entry point is http://localhost:8080 (nginx port), not 8000 (backend port direct) — matches docker-compose.yml nginx service binding"
  - "Copyright year set to 2025 (project inception year) per CLAUDE.md spec"
  - "CONTRIBUTING.md uses single Celery worker command with all three queues for dev simplicity — production uses separate orfs-worker and background-worker processes as per architecture"
metrics:
  duration_minutes: 2
  completed_date: "2026-03-14"
  tasks_completed: 2
  files_created: 3
  files_modified: 0
---

# Quick Task 1: Add Missing Root-Level Documentation Summary

Three mandatory open-source project files created: README.md (5-minute deploy guide), LICENSE
(full Apache 2.0 text), and CONTRIBUTING.md (development setup and contribution guidelines).

## Tasks Completed

| Task | Name | Commit | Files |
|---|---|---|---|
| 1 | Create README.md | 95a6c51 | README.md (153 lines) |
| 2 | Create LICENSE and CONTRIBUTING.md | 89fb78a | LICENSE (184 lines), CONTRIBUTING.md (105 lines) |

## Files Created

**README.md** (153 lines)
- One-line tagline matching CLAUDE.md description
- What It Is: 3-sentence project description
- Prerequisites: Docker 24+, RAM/CPU guidance
- Quick Start: 5 numbered steps (clone → configure → PDK → compose up → open browser)
- Services table: all 9 services with ports and purposes
- PDK Setup: SKY130 instructions, link to open-pdks
- Environment Variables: must-change table (JWT_SECRET_KEY, VNC_TOKEN_SECRET, POSTGRES_PASSWORD) + tuning knobs table
- Resource Sizing: DL380 Gen9 context from CLAUDE.md, EPYC recommendation
- Architecture: one-sentence summary with link to CLAUDE.md
- Updates section: pull + rebuild workflow

**LICENSE** (184 lines)
- Canonical Apache License 2.0 text from apache.org
- Copyright line: `Copyright 2025 ChipAtelier Contributors`
- No modifications to boilerplate text

**CONTRIBUTING.md** (105 lines)
- Ways to contribute: bugs, assignments, code, docs
- Development Setup: 6-step local dev workflow using `uv`, `npm`
- Code Standards: ruff/mypy/pytest, TypeScript strict, conventional commits, Alembic-only migrations
- PR Process: issue-first workflow, 5-step checklist
- Assignment Library: directory structure and validation requirement
- What NOT to Submit: PDK files, model weights, telemetry code
- License agreement notice

## Key Decisions

1. **Entry point port is 8080 not 8000** — README correctly routes users through nginx (port 8080) rather than the bare FastAPI backend (port 8000). This matches `docker-compose.yml` where nginx binds `8080:80` and there is no host-exposed port for the backend.

2. **Copyright year 2025** — used project inception year from CLAUDE.md spec rather than current date (2026), as this is the canonical copyright year for the initial release.

3. **Single worker command in CONTRIBUTING.md for dev** — the dev setup uses one Celery worker consuming all three queues (`orfs_jobs`, `high_priority`, `background`) for simplicity. The production architecture with separate `orfs-worker` and `background-worker` processes is preserved in `docker-compose.yml` and CLAUDE.md.

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

All plan verification checks passed:
- README.md: 153 lines (min 80 required) — PASS
- LICENSE: contains "Apache License" — PASS
- CONTRIBUTING.md: contains "docker compose" and "Development Setup" — PASS
- README.md: contains "Quick Start", "docker compose", ".env.example" — PASS

## Self-Check

- [x] README.md exists at `/opt/developments/chipatelier/README.md` — 153 lines
- [x] LICENSE exists at `/opt/developments/chipatelier/LICENSE` — 184 lines
- [x] CONTRIBUTING.md exists at `/opt/developments/chipatelier/CONTRIBUTING.md` — 105 lines
- [x] Commit 95a6c51 exists (Task 1)
- [x] Commit 89fb78a exists (Task 2)

## Self-Check: PASSED
