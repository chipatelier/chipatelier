---
phase: quick
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - README.md
  - LICENSE
  - CONTRIBUTING.md
autonomous: true
requirements: [DOCS-ROOT]

must_haves:
  truths:
    - "A new contributor can clone the repo and deploy in under 5 minutes using README.md"
    - "The project is unambiguously Apache 2.0 licensed via a LICENSE file"
    - "Contributors know how to submit issues and PRs via CONTRIBUTING.md"
  artifacts:
    - path: "README.md"
      provides: "5-minute deploy guide — the most important file per CLAUDE.md"
      min_lines: 80
    - path: "LICENSE"
      provides: "Apache 2.0 full license text"
      contains: "Apache License"
    - path: "CONTRIBUTING.md"
      provides: "Contribution guidelines for the open-source project"
      min_lines: 40
  key_links:
    - from: "README.md"
      to: "docker-compose.yml"
      via: "docker compose up -d"
      pattern: "docker compose"
    - from: "README.md"
      to: ".env.example"
      via: "cp .env.example .env"
      pattern: "\\.env\\.example"
---

<objective>
Create the three missing root-level documentation files: README.md, LICENSE, and CONTRIBUTING.md.

Purpose: ChipAtelier is described in CLAUDE.md as an open-source project targeting university deployment. These files are mandatory for any open-source repo and are currently absent. README.md is explicitly called "the most important file" in CLAUDE.md.
Output: README.md (5-minute deploy guide), LICENSE (Apache 2.0), CONTRIBUTING.md (contribution guide)
</objective>

<execution_context>
@/home/ajithkv/.claude/get-shit-done/workflows/execute-plan.md
@/home/ajithkv/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@./docker-compose.yml
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create README.md — 5-minute deploy guide</name>
  <files>README.md</files>
  <action>
Write a README.md that lives up to "5-minute deploy guide (most important file)" from CLAUDE.md.

Structure and required content:

# ChipAtelier

One-line tagline: "Browser-based RTL-to-GDS ASIC learning platform for universities — no local EDA tools required."

## What it is
2-3 sentence description. Students submit Verilog, get a routed layout with metrics, entirely in a browser on shared university hardware. Powered by OpenROAD flow scripts (ORFS). Apache 2.0.

## Prerequisites
- Docker Engine 24+ and Docker Compose v2
- 16+ GB RAM, 8+ CPU cores recommended (28-36 cores for 30-40 students)
- PDK files for SKY130 (see PDK Setup section)
- Git

## Quick Start (5 minutes)
Numbered steps:
1. `git clone https://github.com/chipatelier/chipatelier && cd chipatelier`
2. `cp .env.example .env` — then edit .env (highlight JWT_SECRET_KEY and VNC_TOKEN_SECRET as MUST change)
3. PDK setup: `export PDK_ROOT=/data/pdks` and point to SKY130 PDK directory in .env
4. `docker compose up -d`
5. Open http://localhost:8000 — default admin: admin@example.com / changeme (change immediately)

## Services
Brief table: service name, port, purpose. Include: frontend (3000), backend API (8000), PostgreSQL (5432), Redis (6379), MinIO (9000/9001), Celery workers, AI service (11434 Ollama).

## PDK Setup
Short section: SKY130 is the only supported PDK for MVP. Point to open-pdks or sky130A. Set PDK_ROOT in .env.

## Environment Variables
Refer to .env.example for full list. Highlight the 3 variables that MUST be changed for production:
- JWT_SECRET_KEY
- VNC_TOKEN_SECRET
- POSTGRES_PASSWORD

## Resource Sizing
Single-server guidance from CLAUDE.md: dual Xeon E5-2600 (28-36 cores) tested. Recommend EPYC or Xeon Scalable for 30-40 concurrent students. JOB_CPU_CORES, JOB_RAM_GB, MAX_CONCURRENT_JOBS, MAX_VNC_SESSIONS are the key tuning knobs.

## Architecture
One-sentence summary + link to CLAUDE.md or architecture diagram placeholder. Stack: React + TypeScript frontend, FastAPI backend, Celery workers, PostgreSQL 16, Redis 7, MinIO, OpenROAD containers.

## License
Apache 2.0 — see LICENSE file.

## Contributing
See CONTRIBUTING.md.

Writing rules:
- Commands must be copy-pasteable (use fenced code blocks)
- Do NOT include passwords or real secrets — use placeholder values
- Keep total length under 150 lines — this is a deploy guide, not a manual
- Tone: direct and practical
  </action>
  <verify>
    <automated>test -f /opt/developments/chipatelier/README.md && wc -l /opt/developments/chipatelier/README.md | awk '{if ($1 >= 80) print "PASS: " $1 " lines"; else print "FAIL: only " $1 " lines"}'</automated>
  </verify>
  <done>README.md exists with Quick Start section containing numbered docker compose steps, Services table, and Environment Variables section. A reader with Docker installed can deploy from scratch using only this file.</done>
</task>

<task type="auto">
  <name>Task 2: Create LICENSE (Apache 2.0) and CONTRIBUTING.md</name>
  <files>LICENSE, CONTRIBUTING.md</files>
  <action>
**LICENSE:**
Write the full Apache License 2.0 text. Use the canonical text from apache.org.
- Copyright line: `Copyright 2025 ChipAtelier Contributors`
- Do not modify any other text — use the exact Apache 2.0 boilerplate

**CONTRIBUTING.md:**
Write a contributor guide appropriate for an open-source university tool project.

Structure:

# Contributing to ChipAtelier

## Ways to Contribute
- Bug reports and feature requests (GitHub Issues)
- Assignment library additions (assignments/ directory)
- Bug fixes and features (pull requests)
- Documentation improvements

## Development Setup
Prerequisites: Docker, Python 3.12+, Node.js 20+, uv (Python package manager).

Steps:
1. Fork and clone the repo
2. `cp .env.example .env` — set STORAGE_BACKEND=minio for local dev
3. `docker compose up -d postgres redis minio` — start only infra services
4. Backend: `cd backend && uv sync && uv run uvicorn app.main:app --reload`
5. Frontend: `cd frontend && npm install && npm run dev`
6. Worker: `cd worker && uv run celery -A worker.celery_app worker -Q orfs_jobs,high_priority --loglevel=info`

## Code Standards
- Python: ruff for linting, mypy for type checking, pytest (80% coverage target)
- TypeScript: strict mode, ESLint + Prettier
- Commits: conventional commits (feat:, fix:, docs:, chore:)
- Migrations: Alembic only — never edit database tables manually
- Secrets: always via environment variables — never in code or git

## Pull Request Process
1. Open an issue first for significant changes
2. Branch from main: `git checkout -b feat/your-feature`
3. Write tests for new backend logic
4. Run `cd backend && uv run ruff check . && uv run mypy app/` before pushing
5. PR description must explain what and why

## Assignment Library Contributions
Assignments live in `assignments/`. Each needs: assignment.yaml, design/ (Verilog + SDC), README.md.
See `assignments/lab-01-floorplan-basics/` as the reference example.

## What NOT to Submit
- PDK files (SKY130, GF180, etc.) — licensing issues
- Model weights or large binary files
- Code that phones home or sends design data to external services

## License
By contributing you agree your contributions are licensed under Apache 2.0.

Writing rules:
- Keep CONTRIBUTING.md under 80 lines — contributors should be able to skim it
- Commands must be copy-pasteable
  </action>
  <verify>
    <automated>test -f /opt/developments/chipatelier/LICENSE &amp;&amp; grep -q "Apache License" /opt/developments/chipatelier/LICENSE &amp;&amp; test -f /opt/developments/chipatelier/CONTRIBUTING.md &amp;&amp; grep -q "docker compose" /opt/developments/chipatelier/CONTRIBUTING.md &amp;&amp; echo "PASS: LICENSE and CONTRIBUTING.md exist with expected content" || echo "FAIL"</automated>
  </verify>
  <done>LICENSE contains full Apache 2.0 text with copyright year. CONTRIBUTING.md has Development Setup section with runnable commands. Both files exist at repo root.</done>
</task>

</tasks>

<verification>
After both tasks complete, verify all three files exist and have minimum content:

```bash
# All three files present
ls -la /opt/developments/chipatelier/{README.md,LICENSE,CONTRIBUTING.md}

# README has Quick Start section
grep -q "Quick Start" /opt/developments/chipatelier/README.md && echo "README: Quick Start present"

# README has docker compose command
grep -q "docker compose" /opt/developments/chipatelier/README.md && echo "README: docker compose command present"

# LICENSE is Apache 2.0
grep -q "Apache License" /opt/developments/chipatelier/LICENSE && echo "LICENSE: Apache 2.0 confirmed"

# CONTRIBUTING has dev setup
grep -q "Development Setup" /opt/developments/chipatelier/CONTRIBUTING.md && echo "CONTRIBUTING: Dev setup present"
```
</verification>

<success_criteria>
- README.md: Exists, 80+ lines, contains Quick Start with numbered docker compose steps, Services table, key env var callouts
- LICENSE: Exists, contains full Apache 2.0 text with copyright line
- CONTRIBUTING.md: Exists, 40+ lines, contains Development Setup with runnable commands
- All three files are at the repository root (not in a subdirectory)
</success_criteria>

<output>
After completion, create `.planning/quick/1-add-missing-root-level-documentation/1-SUMMARY.md` with:
- Files created: README.md, LICENSE, CONTRIBUTING.md
- Key content decisions made (e.g., deploy steps, copyright year)
- Any deviations from the plan
</output>
