# Coding Conventions

**Analysis Date:** 2026-03-13

## Naming Patterns

**Files:**
- Python backend: `snake_case.py` (e.g., `orfs_job.py`, `storage_service.py`)
- TypeScript/React: `PascalCase.tsx` for components, `camelCase.ts` for utilities
- Modules/directories: `snake_case` in Python, `camelCase` in TypeScript
- Test files: `test_<module>.py` (pytest) or named alongside component

**Functions:**
- Python: `snake_case` for all functions and methods
- TypeScript: `camelCase` for functions; `PascalCase` for React components
- Private utilities in Python: prefix with `_` (e.g., `_download_workspace`, `_check_project_ownership`)
- React hooks: Always `useXxx` pattern (e.g., `useLogStream`, `useTokenRefresh`)

**Variables:**
- Python: `snake_case` for locals and module-level variables
- TypeScript: `camelCase` for locals and module-level state
- React refs: `<name>Ref` (e.g., `termRef`, `wsRef`, `autoScrollRef`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `LOG_BUFFER_MAX`, `SEPARATOR_FMT`)

**Types:**
- Python: Use type hints via `from typing import` or `from collections.abc import` (Python 3.12+)
- TypeScript: Full strict mode enabled; no `any` unless necessary
- Interfaces: Name as `<Entity>Props` for component props (e.g., `LogTerminalProps`)
- Types for union/literal: `Type | None` for optional, `"status1" | "status2"` for literals

**Database Models/ORM:**
- SQLAlchemy models: `ClassName` following entity naming (e.g., `Run`, `Project`, `User`)
- Database columns: `snake_case` field names (e.g., `created_at`, `stage_completed`)
- Relationships: `relationship_name` in snake_case (e.g., `vnc_sessions`, `runs`)
- Pydantic schemas: `ClassName` matching intent (e.g., `SubmitRequest`, `RunStatusResponse`)

## Code Style

**Formatting:**

Python:
- Line length: 100 characters (configured in `backend/pyproject.toml` via `ruff`)
- Use `ruff` for linting and formatting
- Indentation: 4 spaces (standard Python)
- String quotes: Double quotes (`"`) preferred, single OK for inline

TypeScript/React:
- Line length: 100 characters (inferred from Prettier)
- Use Prettier for formatting (run `npm run format`)
- Indentation: 2 spaces (JavaScript/frontend convention)
- String quotes: Double quotes (`"`)

**Linting:**

Python:
- Tool: `ruff` (configured in `backend/pyproject.toml`)
- Type checking: `mypy` with `strict = true` mode
- Key rule: All imports organized; unused imports flagged

TypeScript:
- Tool: `eslint` (no `.eslintrc` at project root — using Vite defaults; adjust as needed)
- Key rules: unused variables and parameters disallowed
- Command: `npm run lint` in frontend/

**Formatting Tools:**

Python:
- `ruff` handles both linting and formatting
- Run linting: `uv run ruff check app/`
- Format: `uv run ruff format app/`

TypeScript:
- `prettier` for code formatting
- Run: `npm run format` in frontend/
- Config: Uses default Prettier settings (100-char line length inferred from context)

## Import Organization

**Order (Python):**
1. Standard library imports (e.g., `import os`, `from datetime import datetime`)
2. Third-party imports (e.g., `from fastapi import`, `from sqlalchemy import`)
3. Local imports (e.g., `from app.core.config import`, `from app.models.run import`)
4. Blank line between each group

**Order (TypeScript/React):**
1. React and framework imports (e.g., `import { useEffect } from "react"`)
2. Third-party library imports (e.g., `import axios`, `import { Terminal }`)
3. Relative imports from utils/store (e.g., `import { useStore }`)
4. CSS/style imports last (e.g., `import "@xterm/xterm/css/xterm.css"`)
5. Blank line between groups

**Path Aliases:**
- Python: Direct relative imports (no aliases currently)
- TypeScript: Relative paths (`../hooks`, `../../store`)
- No path aliases (tsconfig.json does not use `paths` mapping)

**Import Example (Python):**
```python
from datetime import datetime
import redis
from fastapi import APIRouter, Depends
from sqlalchemy import select
from app.core.config import get_settings
from app.models.run import Run
```

**Import Example (TypeScript):**
```typescript
import { useEffect, useRef } from "react";
import { Terminal } from "@xterm/xterm";
import { useStore } from "../../store";
import "@xterm/xterm/css/xterm.css";
```

## Error Handling

**Python Patterns:**

- Use specific exception types: `HTTPException` for API errors, `ValueError` for validation
- HTTPException from FastAPI: Always specify `status_code`, `detail`, optional `headers`
- Example: `raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")`
- Silent failures for non-critical operations: `except Exception: pass` with comment explaining why
- Worker tasks: Catch all exceptions, update status to "failed", publish to log, then re-raise for Celery retry
- Database queries: Always check `.scalar_one_or_none()` or use `db.get()` for safe retrieval

**TypeScript/React Patterns:**

- No global error handler visible in current code; rely on async/await try-catch
- API calls: Use axios with implicit error handling via response status
- Component errors: Render fallback UI or null gracefully
- Avoid throwing in effects; log to console or state for error tracking

**Log Publishing (Worker):**
- Always publish errors via `publish_line(f"[chipatelier] Error message")` before raising
- Log format: `[chipatelier]` prefix for system messages, raw output for ORFS logs

## Logging

**Framework:** Custom Redis pubsub + list buffer pattern (not standard logging module)

**Backend Logging Patterns:**
- Error logs: Publish to Redis via `publish_line()` in worker tasks
- Job lifecycle: "Starting ORFS job X", "Job X finished with status: Y"
- Database errors: Logged inline; critical failures halt task
- No centralized logger configured; uses print-like redis.publish

**Worker Task Logging:**
- Function: `publish_line(line: str) -> None` publishes to Redis channel `logs:{run_id}` and appends to `logbuf:{run_id}` list
- TTL: `logbuf:{run_id}` expires after 24 hours (86400 seconds)
- Buffer size: Max 5000 lines per run (LRU trimmed)
- Stage separators: Injected as `═══ STAGE_NAME ═══` lines at pattern matches

**Frontend Logging:**
- No explicit logging visible; relies on browser console during development
- WebSocket errors silently trigger reconnect (see `useLogStream.ts`)

**No Console Logs in Tests:**
- Tests suppress output via `AsyncSession(engine, echo=False)` and SQLite in-memory DB

## Comments

**When to Comment:**

- Document non-obvious algorithms or architectural decisions
- Explain why a constraint exists (e.g., "CRITICAL: no network access for security")
- Clarify cryptic regex patterns or stage transition logic
- Mark workarounds with `TODO`, `FIXME`, or `HACK` if applicable

**JSDoc/TSDoc Pattern:**

Python:
- Triple-quoted docstrings for modules, classes, functions
- Format: One-line summary, optional blank line, optional detailed description
- Example from `orfs_job.py`:
  ```python
  def run_orfs_job(self, run_id: str) -> None:
      """Execute an ORFS flow job in an isolated Docker container.

      Status transitions:
          queued → starting → running → complete | failed | timeout | cancelled

      Guarantees:
          - Container is always removed in finally block
          ...
      """
  ```

TypeScript:
- JSDoc-style comments for exported functions and React components
- Single-line comments for implementation details
- Example from `LogTerminal.tsx`:
  ```typescript
  /**
   * LogTerminal — xterm.js terminal for ORFS log streaming.
   *
   * Locked behaviors:
   *   - scrollback: 50000 (not 0/unlimited — prevents OOM on long ORFS runs)
   *   - Auto-scroll enabled by default
   */
  ```

## Function Design

**Size:** Aim for functions under 50 lines; split long functions into helpers
- `run_orfs_job`: 130 lines with clear sections (setup, execution, error handling, cleanup)
- `submit_job`: 48 lines; uses helper functions (`_check_project_ownership`, `_get_project_or_404`)

**Parameters:**
- Python: Type-hint all parameters; use dependency injection for FastAPI routes (`Depends(get_db)`)
- TypeScript: Typed interfaces for props; destructure where logical

**Return Values:**
- Python: Always annotate return type (including `-> None`)
- TypeScript: Infer types from functions; annotate component return as `React.ReactElement`
- Pydantic models: Use `model_validate()` for ORM → schema conversion
- Example: `RunStatusResponse.model_validate(run)` in `jobs.py`

**Async/Await:**
- Python backend: All database operations are async (`AsyncSession`, `async with`)
- Celery tasks: Synchronous (inherit sync SQLAlchemy engine from `DATABASE_URL` conversion)
- TypeScript: Use `async/await` for API calls; WebSocket uses event-driven pattern

**Error Propagation:**
- Worker tasks: Catch, log to Redis, then `raise` to trigger Celery retry
- API routes: Catch and convert to `HTTPException` with appropriate status
- Cleanup tasks: Use `finally` blocks to guarantee resource cleanup (containers, temp files)

## Module Design

**Exports:**
- Python: Define `__all__` if re-exporting; otherwise implicit via public names
- TypeScript: Named exports preferred (no default exports except page components)
- Example `store/index.ts`: Exports `useStore` (named) and `AppStore` type

**Barrel Files:**
- Python: `app/api/routes/__init__.py` does not re-export; imports at app startup in `main.py`
- TypeScript: `app/services/__init__.py` and `frontend/src/components/*/index.ts` provide re-export barrels
- Example: `frontend/src/components/LogTerminal/index.ts` exports `LogTerminal` from `LogTerminal.tsx`

**Dependency Injection (FastAPI):**
- Pattern: Use `Depends()` in route signatures
- Examples:
  - `db: AsyncSession = Depends(get_db)` — database session
  - `user: User = Depends(get_current_user)` — authenticated user
  - `storage: StorageService = Depends(get_storage_service)` — storage abstraction

**Service Layer Pattern:**
- `StorageService` in `backend/app/services/storage_service.py`: Wraps boto3 S3 client
- Always test with mocks; mock_s3 fixture provides moto-backed S3

**Async Context Managers:**
- Used throughout: `async with AsyncSessionLocal() as session:`
- Ensures resource cleanup on exit (connections closed, transactions rolled back)

## ORM/Model Conventions

**SQLAlchemy Models:**
- Location: `backend/app/models/`
- Base: All inherit from `Base` class in `models/base.py`
- Columns: Use `mapped_column()` with type annotations
- Relationships: Use `relationship()` with `back_populates` for bidirectional links
- Default values: Set via `default=` or `server_default=text()`
- Example from `run.py`:
  ```python
  id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True),
      primary_key=True,
      default=uuid.uuid4,
      server_default=text("gen_random_uuid()"),
  )
  ```

**JSONB Columns:**
- Use `JSONBCompatible` type for portability (JSONB on PostgreSQL, JSON on SQLite tests)
- Example: `ppa: Mapped[dict | None] = mapped_column(JSONBCompatible, nullable=True)`

**Timestamps:**
- `created_at`: `DateTime(timezone=True), default=datetime.utcnow`
- `completed_at`: `DateTime(timezone=True), nullable=True` (set by worker on job completion)

## Testing-Related Conventions

**Test File Naming:** `test_<module>.py` in `backend/tests/`

**Test Structure:**
- Helper functions for setup (e.g., `_register_and_login`, `_create_project`)
- Test functions prefixed with `test_`
- Descriptive names: `test_submit_job_unauthenticated` not `test_submit`
- Docstring explaining what is being tested

**Fixtures:**
- Provided in `conftest.py`: `async_session`, `test_client`, `mock_docker`, `mock_s3`, `mock_redis`
- Use `@pytest.fixture(scope="function")` for test isolation

**Mocking Patterns:**
- Celery tasks: `patch("app.core.celery_client.celery_app.send_task")`
- Docker: `patch("docker.from_env")` returns mock container
- S3: `mock_s3` fixture (moto-backed) with pre-created bucket
- Redis: `fakeredis.FakeRedis()` or `AsyncMock()` fallback

---

*Convention analysis: 2026-03-13*
