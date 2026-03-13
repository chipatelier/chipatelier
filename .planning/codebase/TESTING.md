# Testing Patterns

**Analysis Date:** 2026-03-13

## Test Framework

**Runner:**
- Backend: `pytest` 8.x with `pytest-asyncio` for async support
- Frontend: `vitest` 2.x with React Testing Library
- Config files: `backend/pytest.ini`, `frontend/vite.config.ts`

**Assertion Library:**
- Python: Built-in `assert` statements
- TypeScript: Vitest built-in assertions (via `expect()`)

**Run Commands:**

```bash
# Backend
cd backend && uv run pytest tests/                    # Run all backend tests
cd backend && uv run pytest tests/ -v                # Verbose output
cd backend && uv run pytest tests/test_jobs.py       # Single file
cd backend && uv run pytest -k "test_submit"         # Filter by name
cd backend && uv run pytest --tb=short               # Short traceback format

# Frontend
cd frontend && npm test                               # Run all frontend tests
cd frontend && npm run test:ui                       # Interactive UI mode
cd frontend && npm test -- --watch                   # Watch mode
```

**Coverage:**

```bash
# Backend (requires pytest-cov)
cd backend && uv run pytest tests/ --cov=app --cov-report=term-missing

# No explicit coverage commands in frontend; use vitest with --coverage flag
cd frontend && npm test -- --coverage
```

**Async Testing Mode:**
- `backend/pytest.ini`: `asyncio_mode = auto` enables automatic async fixture handling
- All fixtures marked with `@pytest_asyncio.fixture` work seamlessly with `async def test_*()`

## Test File Organization

**Location:**
- Backend: `backend/tests/test_*.py` (co-located with source logic)
- Frontend: Typically co-located with components or in separate test files (pattern not fully established)

**Naming:**
- Python: `test_<module>.py` (e.g., `test_jobs.py`, `test_auth.py`, `test_container.py`)
- TypeScript: Not yet established; follow React Testing Library defaults (e.g., `Component.test.tsx`)

**File Structure:**

```
backend/tests/
├── conftest.py              # Shared fixtures (async_session, test_client, mocks)
├── test_auth.py             # Auth endpoints (register, login, logout, refresh)
├── test_jobs.py             # Job API (submit, status, cancel)
├── test_projects.py         # Project management
├── test_container.py        # Docker container lifecycle
├── test_websocket.py        # WebSocket log streaming
├── test_log_parser.py       # Log parsing and stage detection
├── test_metrics.py          # Metrics extraction
├── test_artifacts.py        # Artifact storage
├── test_tile_generator.py   # KLayout tile generation
├── test_vnc.py              # VNC session management
├── test_users.py            # User endpoints
├── test_task1_skeleton.py   # Phase 1 skeleton tests
└── test_task2_infra.py      # Phase 2 infrastructure tests
```

## Test Structure

**Suite Organization:**

```python
# From test_jobs.py — typical structure
import uuid
from unittest.mock import MagicMock, patch
import pytest
from app.models.project import Project
from app.models.run import Run
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(client):
    """Helper: create user, return JWT token."""
    email = f"job_{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/v1/auth/register", json={...})
    r = client.post("/api/v1/auth/login", json={...})
    return r.json()["access_token"]

def auth_headers(token):
    """Helper: return Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_submit_job(test_client, mock_redis):
    """Test description matching test function."""
    # Arrange
    token = _register_and_login(test_client)
    proj_id = _create_project(test_client, token, "submit_proj")

    # Act
    with patch("app.core.celery_client.celery_app.send_task") as mock_task:
        resp = test_client.post(...)

    # Assert
    assert resp.status_code == 202
```

**Patterns:**

**Setup (Arrange):**
- Use helper functions to reduce test boilerplate
- Pre-populate fixtures (users, projects) before testing
- Mock external dependencies at the boundary

**Execution (Act):**
- Single action per test
- Use context managers for mock patches: `with patch(...) as mock:`
- Isolate HTTP requests or database mutations

**Verification (Assert):**
- One primary assertion per test (multiple OK for related assertions)
- Check status codes, response structure, side effects
- Use descriptive assertion messages (implicit in pytest)

**Teardown:**
- Automatic via `async_session` fixture (rollback on exit)
- Mock cleanup automatic via `patch` context manager
- No explicit cleanup needed

## Mocking

**Framework:** `unittest.mock` (Python standard library)

**Celery Task Mocking:**
```python
# Pattern: Mock send_task, not the task itself
with patch("app.core.celery_client.celery_app.send_task") as mock_task:
    mock_result = MagicMock()
    mock_result.id = "celery-task-id-abc123"
    mock_task.delay.return_value = mock_result  # For .delay() calls
    mock_task.return_value = mock_result        # For .send_task() calls
```

**Docker SDK Mocking:**
```python
# Pattern: Mock docker.from_env() globally
@pytest.fixture(scope="function")
def mock_docker():
    with patch("docker.from_env") as mock:
        mock_container = MagicMock()
        mock_container.logs.return_value = iter([b"test log line\n"])
        mock_container.wait.return_value = {"StatusCode": 0}
        mock.return_value.containers.run.return_value = mock_container
        yield mock
```

**S3/MinIO Mocking (via Moto):**
```python
# Pattern: Use moto to mock boto3 S3 client
@pytest.fixture(scope="function")
def mock_s3():
    from moto import mock_aws
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1", ...)
        client.create_bucket(Bucket="chipatelier-artifacts")
        yield client
```

**Redis Mocking (via Fakeredis):**
```python
# Pattern: Fakeredis FakeRedis() instance
@pytest.fixture(scope="function")
def mock_redis():
    import fakeredis.aioredis as fr
    yield fr.FakeRedis()  # Falls back to AsyncMock if import fails
```

**Database Dependency Override:**
```python
# Pattern: Override FastAPI dependency in test
@pytest.fixture(scope="function")
def test_client(async_session):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db

    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
```

**What to Mock:**
- External services: Celery tasks, Docker, S3, Redis
- Expensive operations: Don't call real APIs; use moto/fakeredis
- System calls: `docker.from_env()`, `boto3.client()`

**What NOT to Mock:**
- Database models (use in-memory SQLite via `async_session` fixture)
- FastAPI routing and dependency injection (rely on test client)
- Pydantic schema validation (verify the real behavior)
- Authentication functions (test with real JWT generation)

## Fixtures and Factories

**Test Data Fixtures:**

From `conftest.py`:

```python
@pytest_asyncio.fixture(scope="session")
async def async_engine():
    """Session-scoped SQLite in-memory engine with schema."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine):
    """Function-scoped session with rollback on teardown."""
    session_factory = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
        await session.rollback()

@pytest.fixture(scope="function")
def test_client(async_session):
    """TestClient with get_db dependency overridden."""
    # [See pattern above]
    yield client
```

**Test Data Creation:**

From `test_jobs.py`:

```python
def _register_and_login(client):
    """Create user and return JWT token."""
    email = f"job_{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Test1234!",
        "display_name": "Test User",
    })
    r2 = client.post("/api/v1/auth/login", json={"email": email, "password": "Test1234!"})
    return r2.json()["access_token"]

def _create_project(client, token, name="test_proj"):
    """Create a project and return its ID."""
    r = client.post(
        "/api/v1/projects",
        json={"name": name, "pdk": "sky130hd"},
        headers=auth_headers(token),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]
```

**Location:**
- Fixtures: `backend/tests/conftest.py` (session and function scope)
- Test data helpers: Inline in test files as `_helper_name()` functions
- No factory pattern used; rely on direct API calls

## Coverage

**Requirements:**
- Target: 80% code coverage (not enforced; aspirational)
- No coverage reports in CI/CD configuration visible
- Use `pytest --cov=app --cov-report=term-missing` to generate reports locally

**View Coverage:**

```bash
# Backend
cd backend
uv run pytest tests/ --cov=app --cov-report=html  # Generates htmlcov/
open htmlcov/index.html

# Frontend (if configured)
cd frontend
npm test -- --coverage
```

## Test Types

**Unit Tests:**
- Scope: Individual function or route handler
- Approach: Isolated, with all dependencies mocked
- Example: `test_submit_job` mocks Celery, verifies Run record created in DB
- Coverage: Core business logic, error cases, edge conditions

**Integration Tests:**
- Scope: API endpoint → service → database
- Approach: Real database (in-memory SQLite), real Pydantic models, mocked external APIs
- Example: `test_single_active_run_constraint` tests concurrent run behavior
- Run with: `pytest -m integration` (if marked with `@pytest.mark.integration`)

**End-to-End Tests:**
- Currently: Not visible in test suite
- Would cover: Full job submission → container spawning → log streaming
- Not run in CI (too expensive); manual testing or Docker Compose integration tests

**E2E Test Pattern (when added):**
- Requires live Docker daemon, Redis, PostgreSQL
- May use Docker Compose for orchestration
- Example: `docker-compose -f docker-compose.test.yml up --abort-on-container-exit`

## Common Patterns

**Async Testing:**

```python
# Pattern: Mark with @pytest.mark.asyncio OR use @pytest_asyncio.fixture
@pytest.mark.asyncio
async def test_async_operation():
    async_session = ...  # from fixture
    # Queries automatically wrapped in async context
    user = await async_session.get(User, user_id)
    assert user is not None

# Alternatively, if using pytest.ini with asyncio_mode=auto:
async def test_another_async_operation(async_session):
    # No decorator needed; pytest-asyncio auto-handles it
    pass
```

**Error Testing:**

```python
# Pattern: Assert HTTP error status codes
def test_submit_job_unauthenticated(test_client):
    """POST /api/v1/jobs/submit returns 401 without a token."""
    resp = test_client.post("/api/v1/jobs/submit", json={"project_id": str(uuid.uuid4())})
    assert resp.status_code == 401

# Pattern: Check exception messages
def test_cancel_completed_job_returns_400(test_client, async_session):
    """DELETE /api/v1/jobs/{id} on completed run returns 400."""
    # ... setup ...
    cancel_again = test_client.delete(f"/api/v1/jobs/{run_id}", ...)
    assert cancel_again.status_code == 400
    # Optional: assert "error detail" in cancel_again.json()
```

**State Mutation Testing:**

```python
# Pattern: Verify database state changed
def test_cancel_queued_job(test_client):
    # Arrange & Act
    submit_resp = test_client.post("/api/v1/jobs/submit", ...)
    run_id = submit_resp.json()["run_id"]

    # Act: Cancel
    cancel_resp = test_client.delete(f"/api/v1/jobs/{run_id}", ...)

    # Assert: Verify status changed
    status_resp = test_client.get(f"/api/v1/jobs/{run_id}", ...)
    assert status_resp.json()["status"] == "cancelled"
```

**Dependency Override Testing:**

```python
# Pattern: Override Redis during auth tests
@pytest.mark.asyncio
async def test_logout_invalidates_refresh(test_client, mock_redis):
    from app.main import app
    from app.core.redis import get_redis

    async def override_redis():
        return mock_redis

    app.dependency_overrides[get_redis] = override_redis

    try:
        # Test code using mock_redis
        pass
    finally:
        app.dependency_overrides.clear()
```

**Worker Task Testing:**

Pattern for testing Celery tasks (when needed):

```python
# Mock the task execution without Celery
def test_orfs_job_container_cleanup(mock_docker):
    """Verify container is stopped and removed even on error."""
    from worker.tasks.orfs_job import run_orfs_job
    from worker.container.manager import ContainerManager

    # Arrange: Mock container manager
    with patch.object(ContainerManager, "stop_and_remove") as mock_stop:
        # Act: Call task (or mock its execution)
        # Assert: Verify cleanup was called
        mock_stop.assert_called_once()
```

**WebSocket Testing:**

```python
# Pattern: Mock WebSocket connection and message handling
def test_log_stream_connection(test_client, mock_redis):
    """Verify WebSocket connects and streams log lines."""
    # [Setup run]
    # [Mock Redis publish]
    # [Connect WebSocket via test client]
    # [Verify message received]
```

## Test Markers

**Available Markers** (from `pytest.ini`):

```ini
markers =
    integration: marks tests as integration tests (requires running services)
```

**Usage:**

```python
@pytest.mark.integration
def test_full_job_flow():
    """Requires Docker, PostgreSQL, Redis running."""
    pass

# Run only integration tests:
# pytest -m integration

# Run all except integration:
# pytest -m "not integration"
```

## Known Gaps

**Areas without test coverage (as of now):**
- E2E job submission → container execution → artifact storage
- VNC session lifecycle and WebSocket reconnection logic
- Log streaming under network failure
- Tile generation background task
- Metrics extraction and PPA calculation
- Admin endpoints (leaderboard, queue status)

**Frontend testing:**
- No Vitest setup visible in current phase
- React components not yet tested
- Plan: Add React Testing Library tests in Phase 2+

---

*Testing analysis: 2026-03-13*
