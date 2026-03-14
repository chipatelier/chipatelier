# Contributing to ChipAtelier

Thank you for contributing to an open-source tool that makes chip design education more accessible.

## Ways to Contribute

- **Bug reports and feature requests** — open a GitHub Issue with a clear description
- **Bug fixes and features** — submit a pull request
- **Assignment library** — add lab exercises to `assignments/` (great first contribution)
- **Documentation improvements** — fix errors, add examples, improve clarity

## Development Setup

Prerequisites: Docker, Python 3.12+, Node.js 20+, [uv](https://docs.astral.sh/uv/) (Python package manager).

**1. Fork and clone**

```bash
git clone https://github.com/<your-fork>/chipatelier && cd chipatelier
```

**2. Configure environment**

```bash
cp .env.example .env
# Set STORAGE_BACKEND=minio for local dev (default)
```

**3. Start infrastructure services only**

```bash
docker compose up -d postgres redis minio
```

**4. Start backend (with hot reload)**

```bash
cd backend && uv sync && uv run uvicorn app.main:app --reload
```

**5. Start frontend (with hot reload)**

```bash
cd frontend && npm install && npm run dev
```

**6. Start Celery worker**

```bash
cd worker && uv run celery -A celery_app worker \
  -Q orfs_jobs,high_priority,background \
  --loglevel=info
```

The API is available at `http://localhost:8000`. The frontend dev server runs at `http://localhost:5173`.

## Code Standards

- **Python:** `ruff` for linting, `mypy` for type checking, `pytest` for tests (80% coverage target)
- **TypeScript:** strict mode, ESLint + Prettier
- **Commits:** [conventional commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `docs:`, `chore:`, `test:`
- **Migrations:** Alembic only — never modify database tables manually in production or tests
- **Secrets:** always via environment variables — never hardcoded in source or committed to git

Run checks before pushing:

```bash
# Backend
cd backend && uv run ruff check . && uv run mypy app/ && uv run pytest

# Frontend
cd frontend && npm run lint && npm run typecheck
```

## Pull Request Process

1. **Open an issue first** for significant changes — discuss the approach before writing code
2. **Branch from main:** `git checkout -b feat/your-feature`
3. **Write tests** for new backend logic
4. **Pass all checks** (ruff, mypy, pytest) before pushing
5. **PR description must explain** what the change does and why it is needed
6. A maintainer will review and merge — expect feedback within a few days

## Assignment Library Contributions

Assignments live in `assignments/`. Each assignment directory needs:

- `assignment.yaml` — objectives, checkpoints, editable/locked params (see schema below)
- `design/` — starter Verilog source and SDC timing constraints
- `README.md` — student-facing instructions for the lab

Use `assignments/lab-01-floorplan-basics/` as the reference example.
Test your assignment by running the full ORFS flow locally before submitting.

## What NOT to Submit

- PDK files (SKY130, GF180, etc.) — these have their own distribution licenses
- Pre-trained model weights or large binary files
- Code that sends design data, logs, or student information to external services
- Modifications to platform-level ORFS variables (`TECH_LEF`, `LIB_FILES`, etc.)

## License

By contributing you agree that your contributions are licensed under
[Apache 2.0](./LICENSE), the same license as ChipAtelier.
