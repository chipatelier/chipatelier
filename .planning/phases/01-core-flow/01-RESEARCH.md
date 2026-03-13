# Phase 1: Core Flow - Research

**Researched:** 2026-03-13
**Domain:** Full-stack web application — FastAPI + Celery + Redis + PostgreSQL + Docker SDK + MinIO + noVNC + React/xterm.js
**Confidence:** HIGH (all critical stack decisions verified against official docs and authoritative sources)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Main portal layout:**
- After login, user lands on a project list/grid (card per project showing project name + run count)
- "New Project" button prominent in the header
- Run detail screen uses tabbed layout: Logs | Results | Config
- Flow stage progress (Synth → Floorplan → Place → CTS → Route → GDS) is always visible in a persistent status bar above the tabs — user never has to switch tabs to check stage progress
- Navigation uses breadcrumb: Projects → [project name] → run #N
- Project page shows a run list table (status, timestamp, target stage, key PPA metrics); click to open run detail
- Run/Cancel button lives in the header area alongside stage status bar

**Log terminal experience:**
- Auto-scroll on by default; pauses automatically if user scrolls up to review; "Jump to bottom" button appears when paused; auto-scroll resumes when user scrolls back to bottom
- Stage transitions injected as separator lines in the terminal output (e.g. `═══ FLOORPLAN ══════════════════════`) in a distinct style — makes it easy to scan and find where each stage starts
- Unlimited scrollback in the browser (no xterm.js scrollback cap)
- When a new run starts, navigate to the new run's detail page with a fresh terminal; prior run's logs preserved and accessible via the project's run list

**Results & metrics display:**
- PPA metrics shown as cards in the Results tab: WNS, TNS, DRC violation count, core area, total power — each with label + value + color indicator (green/yellow/red based on thresholds)
- Static layout PNG displayed in the Results tab, below the metric cards, large enough to see the design shape
- "Open in VNC viewer" button directly below the layout PNG
- Results tab is disabled/greyed out while job is running; automatically activates and switches to it when job completes
- Download links for GDS, DEF, and timing reports also in the Results tab

**File upload & re-run flow:**
- Multi-file Verilog upload: students can upload multiple .v/.sv files; one is designated as the top module
- "New Run" forks config.mk from the last run of the project by default; student tweaks parameters and submits; source files reused unless explicitly replaced — fast iteration loop
- Only one active run per project at a time; the "New Run" button is disabled while a run is running; student must cancel the active run before starting a new one (no queuing confusion)

### Claude's Discretion
- Empty state design for project list (first-time user, no projects yet)
- Exact loading skeleton / spinner designs
- Config tab content in Phase 1 (raw config.mk view; guided form mode is Phase 2)
- Error state handling for failed jobs in terminal vs. results tab
- Storage usage display placement within the UI (DASH-04 requirement: show "X GB of Y GB used")

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-01 | User can create an account with email and password | argon2-cffi for hashing; Alembic users table migration; FastAPI registration endpoint |
| AUTH-02 | User can log in and receive a JWT access token (15min) + httpOnly refresh cookie (7 days) | PyJWT 2.10.x encode/decode; FastAPI Response.set_cookie with httponly=True, secure=True, samesite="lax" |
| AUTH-03 | User can log out from any page (refresh cookie invalidated) | Refresh token denylist in Redis (SET with TTL = remaining token lifetime); cookie cleared on logout |
| AUTH-04 | Session persists across browser refresh via automatic access token renewal | Axios interceptor: 401 → POST /auth/refresh → retry; refresh cookie sent automatically by browser |
| JOB-01 | User can create a project and upload Verilog source files and config.mk | FastAPI multipart upload; boto3 to MinIO; source_versions table row insert |
| JOB-02 | Job runs in isolated Docker container with no network and cgroup limits | Docker SDK `client.containers.run()` with mem/cpu/network=none/read-only flags; finally block cleanup |
| JOB-03 | User sees live log output streaming in xterm.js during execution | Redis PUBLISH from container log thread; FastAPI WS subscribes and pushes; @xterm/addon-attach |
| JOB-04 | User sees job status and stage-level progress | Stage regex detection in log streamer; DB status updates; Zustand store polling or WS push |
| JOB-05 | User can cancel a running job | Celery task revoke + container stop/remove; status set to cancelled |
| RSLT-01 | PPA metrics visible after completion | Parse metadata-base-ok.json / reports/*/6_final_metrics.json from workspace; store in runs.ppa JSONB |
| RSLT-02 | Download links for GDS, DEF, timing reports | boto3 presigned URLs (1hr expiry); served via /api/v1/jobs/{id}/artifacts endpoint |
| RSLT-03 | Static layout PNG within seconds of job completion | KLayout headless `pya.LayoutView` → `save_image_with_options()`; background Celery task on completion |
| RSLT-04 | Full run history for a project | runs table query ordered by created_at; Pydantic schema including ppa JSONB fields |
| LAYT-01 | VNC viewer tab opens OpenROAD Qt GUI with DEF pre-loaded | noVNC + websockify container; HMAC-signed token; Nginx proxy_pass validation; supervisord for Xvfb + x11vnc |
| DASH-04 | User sees current storage usage | SUM(storage_bytes) per user from runs table; displayed in header or project page sidebar |
</phase_requirements>

---

## Summary

Phase 1 builds the entire full-stack RTL-to-GDS pipeline: infrastructure (Docker Compose, PostgreSQL, Redis, MinIO, Celery), authentication, job submission and container lifecycle, live log streaming, artifact storage, PPA metrics display, static layout PNG, and the VNC viewer tab. The stack is well-defined in CLAUDE.md and all core technology choices are locked. This is a greenfield project so there is no migration burden from existing code.

The most complex integration challenges are: (1) the Redis pub/sub → WebSocket → xterm.js log streaming chain, including correct handling of reconnects, log replay for late-joiners, and LTRIM/TTL guards to prevent unbounded memory growth; (2) the Docker SDK container lifecycle with cgroup v2 enforcement, finally-block cleanup, and the orphaned-container watchdog; (3) the VNC session routing where Nginx must validate an HMAC token before proxying WebSocket traffic to the correct container port.

A critical project-level constraint from CLAUDE.md: the fast-path single PNG layout snapshot is a permanent path — it must never be removed or merged with the tile generation pipeline (which is Phase 2). Build it robustly in Phase 1, not as a placeholder.

**Primary recommendation:** Build Plan 01-01 (infrastructure) first as a complete working Docker Compose stack with empty-but-running services, then implement plans 01-02 through 01-06 in sequence, since each plan depends on the database schema and service connectivity established in 01-01.

---

## Standard Stack

### Core Backend
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.115.x | Web framework + OpenAPI | Async, auto-OpenAPI, HTTPException model |
| uvicorn[standard] | 0.32.x | ASGI server | Official recommended runner for FastAPI |
| sqlalchemy[asyncio] | 2.0.x | ORM | Async-native in 2.0; DeclarativeBase; type-safe |
| asyncpg | 0.29.x | PostgreSQL async driver | Fastest Python asyncio PG driver; SA 2.0 official |
| alembic | 1.13.x | DB migrations | Standard SQLAlchemy migration tool; async template `-t async` |
| pydantic | 2.x | Schema validation | FastAPI native; V2 much faster than V1 |
| pydantic-settings | 2.x | Config from env vars | Official pydantic pattern; `.env` file support |
| PyJWT | 2.10.x | JWT encode/decode | Replaces python-jose (deprecated); simpler API |
| argon2-cffi | 25.x | Password hashing | Replaces passlib/bcrypt; Argon2id is current standard |
| celery[redis] | 5.4.x | Task queue | Mature; Redis broker + result backend; queue routing |
| redis[asyncio] | 5.x | Broker + pub/sub + cache | asyncio support via redis.asyncio module |
| boto3 | 1.35.x | MinIO/S3 storage | Endpoint-switchable between MinIO and AWS S3 |
| docker | 7.1.x | Container lifecycle | Official Docker SDK for Python |
| httpx | 0.27.x | Async HTTP client | FastAPI testing; TestClient uses httpx |

### Core Frontend
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | 18.3.x | UI framework | Locked in CLAUDE.md |
| typescript | 5.6.x | Type safety | Strict mode; generates types from OpenAPI |
| vite | 5.4.x | Build tool | Fast dev server; standard for React+TS in 2025 |
| zustand | 5.x | State management | Locked in CLAUDE.md; minimal boilerplate |
| axios | 1.7.x | HTTP client | Interceptor support for 401→refresh retry |
| @xterm/xterm | 5.5.x | Terminal emulator | Industry standard for browser terminals |
| @xterm/addon-fit | 0.10.x | Terminal resize | Required for responsive terminal sizing |
| @xterm/addon-attach | 0.11.x | WebSocket attach | Attaches terminal to WS for streaming |
| @xterm/addon-search | 0.15.x | Terminal search | Optional but valuable for log navigation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-multipart | 0.0.12 | Form data parsing | Required for FastAPI file uploads |
| aiofiles | 24.x | Async file I/O | Writing workspace files before container start |
| pytest | 8.x | Test runner | Backend unit and integration tests |
| pytest-asyncio | 0.24.x | Async test support | All FastAPI/SQLAlchemy async tests |
| anyio | 4.x | Async testing backend | httpx AsyncClient + pytest-asyncio |
| vitest | 2.x | Frontend test runner | Vite-native; fast; compatible with jest API |
| @testing-library/react | 16.x | Component testing | React Testing Library standard |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyJWT | python-jose | python-jose is deprecated/unmaintained as of 2024; PyJWT is the replacement |
| argon2-cffi | passlib[bcrypt] | passlib is no longer actively maintained; argon2-cffi is the current standard |
| boto3 | minio-py | minio-py has limited presigned multipart support; boto3 works with MinIO via endpoint_url |
| Redis pub/sub | Redis Streams | Streams support replay for late subscribers; however pub/sub is sufficient when combined with log replay endpoint; simpler implementation for Phase 1 |
| @xterm/addon-attach | Custom WS handler | addon-attach is the canonical approach; custom handler adds no value |

**Installation (backend):**
```bash
uv add fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic pydantic pydantic-settings PyJWT argon2-cffi "celery[redis]" "redis[asyncio]" boto3 docker httpx python-multipart aiofiles
uv add --dev pytest pytest-asyncio anyio httpx
```

**Installation (frontend):**
```bash
npm create vite@latest frontend -- --template react-ts
npm install zustand axios @xterm/xterm @xterm/addon-fit @xterm/addon-attach @xterm/addon-search
npm install -D vitest @testing-library/react @testing-library/user-event @vitejs/plugin-react
```

---

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── app/
│   ├── api/
│   │   ├── routes/          # One file per domain (auth, jobs, projects, artifacts, vnc)
│   │   └── websocket.py     # WS log streaming endpoint
│   ├── models/              # SQLAlchemy ORM models (Base, User, Run, Project, VncSession)
│   ├── schemas/             # Pydantic in/out schemas, one per domain
│   ├── services/            # Business logic (job_service, storage_service, auth_service)
│   ├── core/
│   │   ├── config.py        # pydantic-settings Settings class
│   │   ├── database.py      # async_engine, AsyncSession factory, get_db dependency
│   │   ├── redis.py         # Redis connection pool
│   │   └── security.py      # PyJWT encode/decode, argon2 hash/verify, HMAC VNC token
│   └── main.py              # FastAPI app, lifespan, CORS, router include
├── alembic/                 # Async migrations; env.py uses run_async_migrations pattern
├── tests/
│   ├── conftest.py          # Async engine, session rollback fixtures, TestClient
│   └── test_*.py

worker/
├── tasks/
│   ├── orfs_job.py          # Main ORFS task (queue: orfs_jobs)
│   ├── tile_generator.py    # KLayout PNG generation (queue: background)
│   └── vnc_session.py       # VNC container lifecycle (queue: background)
├── container/
│   └── manager.py           # Docker SDK wrapper
└── celeryconfig.py          # Queue routing table

frontend/
├── src/
│   ├── components/
│   │   ├── LogTerminal/     # xterm.js + WS hook
│   │   ├── StageStatusBar/  # Synth✓ Floor↻ Place- etc.
│   │   ├── PpaMetricCards/  # WNS/TNS/DRC cards with color indicators
│   │   ├── LayoutSnapshot/  # Static PNG + VNC launcher button
│   │   └── RunHistoryTable/ # Sortable run list with PPA columns
│   ├── pages/
│   │   ├── ProjectListPage.tsx
│   │   ├── ProjectPage.tsx  # Run list table
│   │   └── RunDetailPage.tsx # Tabbed: Logs | Results | Config
│   ├── hooks/
│   │   ├── useLogStream.ts  # WS connection + auto-scroll state machine
│   │   └── useTokenRefresh.ts # Axios interceptor setup
│   ├── api/                 # Generated or hand-typed axios wrappers
│   └── store/               # Zustand slices: auth, projects, runs, jobs
```

### Pattern 1: Async SQLAlchemy Session Dependency
**What:** FastAPI dependency that provides a scoped async session per request, always closed on exit.
**When to use:** Every route that touches the database.
```python
# Source: https://fastapi.tiangolo.com/tutorial/sql-databases/
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

### Pattern 2: JWT + httpOnly Refresh Cookie
**What:** Short-lived access token in response body; long-lived refresh token in httpOnly cookie.
**When to use:** All authenticated endpoints. Refresh token must NOT be accessible to JS.
```python
# Source: FastAPI docs + STATE.md decision (PyJWT 2.10.x)
import jwt
from datetime import datetime, timedelta, timezone

def create_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "refresh",
        "jti": str(uuid4()),  # unique ID for denylist
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")

# In login route:
response.set_cookie(
    key="refresh_token",
    value=refresh_token,
    httponly=True,
    secure=True,       # HTTPS only
    samesite="lax",
    max_age=7 * 86400,
    path="/api/v1/auth/refresh",  # scope cookie to refresh endpoint only
)
```

### Pattern 3: Celery Queue Routing — Two Dedicated Worker Processes
**What:** Two separate Celery worker processes: one consuming `orfs_jobs`, one consuming `background`.
**When to use:** Never share ORFS workers with tile/VNC/AI tasks. ORFS jobs can saturate workers for hours.
```python
# Source: Celery docs — https://docs.celeryq.dev/en/stable/userguide/routing.html
# worker/celeryconfig.py
task_routes = {
    "worker.tasks.orfs_job.*": {"queue": "orfs_jobs"},
    "worker.tasks.tile_generator.*": {"queue": "background"},
    "worker.tasks.vnc_session.*": {"queue": "background"},
}
task_queues = {
    "orfs_jobs": {"exchange": "orfs_jobs"},
    "background": {"exchange": "background"},
}

# docker-compose.yml: two separate worker services
# orfs-worker: celery -A worker worker -Q orfs_jobs -c 4
# background-worker: celery -A worker worker -Q background -c 2
```

### Pattern 4: Docker SDK Container Lifecycle with Cleanup
**What:** Spawn ORFS container, stream logs to Redis, always remove container in finally block.
**When to use:** Every job execution. Orphaned containers are a system-killing bug.
```python
# Source: Docker SDK docs — https://docker-py.readthedocs.io/en/stable/containers.html
import docker

client = docker.from_env()

def run_orfs_job(run_id: str, workspace: str, pdk_root: str, settings: dict):
    container = None
    try:
        container = client.containers.run(
            image=settings["ORFS_IMAGE"],
            command=["make", f"DESIGN_CONFIG={workspace}/config.mk"],
            name=f"orfs_job_{run_id}",
            detach=True,
            network_mode="none",              # CRITICAL: no network
            cpu_period=100000,
            cpu_quota=int(settings["JOB_CPU_CORES"]) * 100000,
            mem_limit=f"{settings['JOB_RAM_GB']}g",
            memswap_limit=f"{settings['JOB_RAM_GB']}g",  # no swap
            read_only=True,
            tmpfs={"/tmp": "size=512m"},
            user="orfs:orfs",
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            volumes={
                workspace: {"bind": "/workspace", "mode": "rw"},
                pdk_root: {"bind": "/pdks", "mode": "ro"},
            },
            storage_opt={"size": f"{settings['JOB_DISK_GB']}G"},
        )
        for line in container.logs(stream=True, follow=True):
            # publish to Redis, detect stage transitions
            publish_log_line(run_id, line.decode("utf-8", errors="replace"))
        container.wait()
        exit_code = container.attrs["State"]["ExitCode"]
        return exit_code
    finally:
        if container:
            try:
                container.stop(timeout=10)
                container.remove(force=True)
            except docker.errors.NotFound:
                pass  # already gone
```

### Pattern 5: Redis Pub/Sub → WebSocket Log Streaming
**What:** Worker publishes log lines to Redis channel; FastAPI WS endpoint subscribes and pushes to browser.
**When to use:** JOB-03 requirement. Must handle: late-joiners (replay from Redis list), client disconnect, channel expiry.
```python
# Source: https://itnext.io/scalable-real-time-apps-with-python-and-redis-exploring-asyncio-fastapi-and-pub-sub-79b56a9d2b94
import redis.asyncio as aioredis

# Worker side: publish + append to list for replay
async def publish_log_line(run_id: str, line: str):
    r = await get_redis()
    channel = f"logs:{run_id}"
    list_key = f"logbuf:{run_id}"
    await r.publish(channel, line)
    await r.rpush(list_key, line)
    await r.ltrim(list_key, -5000, -1)   # keep last 5000 lines
    await r.expire(list_key, 86400)       # 24hr TTL

# FastAPI WS endpoint
@router.websocket("/jobs/{run_id}/logs/stream")
async def log_stream(ws: WebSocket, run_id: str, ...):
    await ws.accept()
    r = await get_redis()
    # Replay buffered lines first
    buffered = await r.lrange(f"logbuf:{run_id}", 0, -1)
    for line in buffered:
        await ws.send_text(line.decode())
    # Then subscribe for live updates
    pubsub = r.pubsub()
    await pubsub.subscribe(f"logs:{run_id}")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await ws.send_text(message["data"].decode())
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"logs:{run_id}")
```

### Pattern 6: xterm.js Auto-Scroll State Machine
**What:** Auto-scroll enabled by default; pause on user scroll-up; resume on scroll-to-bottom.
**When to use:** LogTerminal component — locked decision from CONTEXT.md.
```typescript
// Source: CONTEXT.md decisions + xterm.js docs https://xtermjs.org/
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";

const term = new Terminal({
  scrollback: 0,           // 0 = unlimited (browser memory is the limit)
  convertEol: true,
  theme: { background: "#1a1a1a" },
});

let autoScroll = true;

term.onScroll(() => {
  // If user scrolled up from the bottom, pause auto-scroll
  const isAtBottom =
    term.buffer.active.viewportY >=
    term.buffer.active.length - term.rows;
  autoScroll = isAtBottom;
  setShowJumpButton(!isAtBottom);
});

function writeLogLine(line: string) {
  term.writeln(line);
  if (autoScroll) {
    term.scrollToBottom();
  }
}
```

### Pattern 7: HMAC-Signed VNC Token
**What:** Short-lived token signed with VNC_TOKEN_SECRET, validated by Nginx auth_request before proxying.
**When to use:** Every VNC session start. Token in URL path, not query string.
```python
# Source: STATE.md decision — VNC token = HMAC-signed JWT with separate VNC_TOKEN_SECRET
import jwt
from datetime import datetime, timedelta, timezone

def create_vnc_token(user_id: str, run_id: str, container_port: int) -> str:
    payload = {
        "sub": user_id,
        "run_id": run_id,
        "port": container_port,
        "exp": datetime.now(timezone.utc) + timedelta(hours=2),
        "type": "vnc",
    }
    return jwt.encode(payload, settings.VNC_TOKEN_SECRET, algorithm="HS256")

# Nginx calls FastAPI /api/v1/vnc/validate?token=... via auth_request
# FastAPI validates token, returns 200 (allowed) or 401 (denied)
# On 200, Nginx sets X-VNC-Port header for proxy_pass to container
```

### Pattern 8: KLayout Headless PNG Generation
**What:** Use KLayout Python API headless (no display) to render DEF/GDS as a PNG.
**When to use:** RSLT-03 — fast-path PNG within seconds of job completion; always a background Celery task.
```python
# Source: KLayout Python API — https://www.klayout.de/doc-qt5/programming/python.html
# + https://github.com/KLayout/klayout/issues/495
import klayout.db as db
import klayout.lay as lay

def generate_layout_png(def_path: str, lef_path: str, output_path: str,
                        width: int = 2048, height: int = 2048):
    layout = db.Layout()
    layout.read(def_path)  # or GDS path
    cell = layout.top_cell()
    bbox = cell.bbox()
    view = lay.LayoutView()
    view.load_layout(layout, True)
    view.max_hier()
    view.save_image_with_options(output_path, width, height, 0, 0, 0, bbox)
```

**Note:** KLayout headless mode requires no display server. Confirmed via KLayout Python API docs (confirmed behavior in klayout.de/forum/discussion/2413). The `lay.LayoutView()` in batch mode works without X11.

### Pattern 9: MinIO Presigned URL for Artifact Downloads
**What:** Generate a time-limited presigned URL for GDS/DEF/report downloads without exposing MinIO credentials.
**When to use:** RSLT-02 — download links in Results tab.
```python
# Source: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html
import boto3
from botocore.config import Config

s3 = boto3.client(
    "s3",
    endpoint_url=settings.MINIO_ENDPOINT_URL,   # e.g. http://minio:9000
    aws_access_key_id=settings.MINIO_ACCESS_KEY,
    aws_secret_access_key=settings.MINIO_SECRET_KEY,
    config=Config(signature_version="s3v4"),     # MinIO requires v4
    region_name="us-east-1",                     # required but arbitrary for MinIO
)

def generate_download_url(bucket: str, key: str, expiry_seconds: int = 3600) -> str:
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expiry_seconds,
    )
```

**Warning:** Use `signature_version="s3v4"` explicitly. boto3 signature v2 fails with MinIO in some configurations (confirmed: minio/minio issue #8132).

### Pattern 10: Zustand Store Slices for Phase 1
**What:** Split state into domain slices. Avoid one monolithic store.
**When to use:** All frontend state. This establishes the pattern Phase 2 will extend.
```typescript
// Source: Zustand docs — https://zustand.docs.pmnd.rs/
// store/authSlice.ts
interface AuthSlice {
  user: User | null;
  accessToken: string | null;
  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
}

// store/jobSlice.ts
interface JobSlice {
  activeRunId: string | null;
  runStatus: RunStatus | null;
  stageProgress: StageProgress;
  setRunStatus: (status: RunStatus) => void;
  setStageProgress: (stage: string, state: "done" | "running" | "pending") => void;
}

// Combined store
export const useStore = create<AuthSlice & JobSlice>()(
  (...a) => ({
    ...createAuthSlice(...a),
    ...createJobSlice(...a),
  })
);
```

### Anti-Patterns to Avoid
- **Shared Celery workers for ORFS and background tasks:** If all 4 workers are consumed by 4 concurrent ORFS jobs, tile generation and VNC startup will queue indefinitely. Use separate worker processes.
- **Storing refresh tokens in localStorage:** JavaScript-accessible; XSS will steal them. Use httpOnly cookie only.
- **Blocking the Celery task on container logs without a timeout:** ORFS jobs can run for up to 2 hours. The Celery worker must stream logs asynchronously; a blocking `.wait()` is fine but must respect `JOB_TIMEOUT_SECONDS` via `socket_timeout` or a watchdog.
- **Auto-updating ORFS image:** Never auto-pull latest; pin the image version after canary passes. A broken ORFS mid-semester is catastrophic.
- **GIN index for leaderboard ordering:** STATE.md records this: `ORDER BY (ppa->>'worst_negative_slack')::numeric` requires a functional B-tree index with `::numeric` cast, NOT a GIN index.
- **Removing the fast-path PNG after Phase 2 adds tiles:** CLAUDE.md explicitly states it must remain as a permanent path.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom bcrypt wrapper | argon2-cffi | Timing attack resistance, memory hardness, OWASP-recommended |
| JWT encode/decode | Custom HMAC token | PyJWT | Handles algorithm confusion attacks, expiry validation, key rotation |
| DB migrations | Manual ALTER TABLE | Alembic | Schema drift, rollback, team consistency |
| File storage | Direct filesystem | MinIO + boto3 | Presigned URLs, lifecycle policies, S3-compatible, quota tracking |
| Terminal emulator | `<div>` with text | @xterm/xterm | ANSI escape codes, scrollback management, performance at scale |
| WebSocket pub/sub | Long-polling | Redis pub/sub + asyncio | Horizontal scale, decoupled worker↔API, low latency |
| Container resource limits | Python subprocess limits | Docker SDK cgroups | Kernel-level enforcement, no workarounds possible by student code |
| Layout rendering | Custom GDS parser | KLayout Python API | GDS format is complex; KLayout handles all PDK layer mappings |
| Artifact URL signing | Expose MinIO directly | boto3 presigned URLs | Credentials never leave backend; time-limited access |

**Key insight:** Every item in this list represents weeks of work and subtle security/correctness bugs. The ecosystem solutions are battle-tested at scale.

---

## Common Pitfalls

### Pitfall 1: Alembic Async Configuration
**What goes wrong:** Alembic default `env.py` uses synchronous connections; fails with asyncpg.
**Why it happens:** Alembic predates widespread async use.
**How to avoid:** Generate alembic with `alembic init -t async alembic`. Update `env.py` to use `run_async_migrations()` pattern with `AsyncConnection`.
**Warning signs:** `RuntimeError: no running event loop` or `greenlet_spawn has not been called` during `alembic upgrade head`.

### Pitfall 2: pytest-asyncio Event Loop Scope Mismatch
**What goes wrong:** Tests fail with `ScopeMismatch: You tried to access the function scoped fixture event_loop in a session scoped fixture`.
**Why it happens:** pytest-asyncio 0.21+ changed event loop scoping defaults.
**How to avoid:** Set `asyncio_mode = "auto"` in `pytest.ini`. Use `@pytest.fixture(scope="session")` with explicit `event_loop_policy` override for session-scoped DB fixtures.
**Warning signs:** Test isolation failures; one test's DB changes leaking into another.

### Pitfall 3: Redis Pub/Sub Messages Lost for Late-Joining WebSocket Clients
**What goes wrong:** Student connects to WS after job is 50% complete; sees only new lines, missing prior log output.
**Why it happens:** Redis pub/sub is fire-and-forget; no message history.
**How to avoid:** Always maintain a `logbuf:{run_id}` Redis List alongside the pub/sub channel. On WS connect, replay the list first, then subscribe. Apply `LTRIM` to cap at 5000 lines and `EXPIRE` to 24hr.
**Warning signs:** Students reporting "terminal shows partial logs on reconnect."

### Pitfall 4: Orphaned ORFS Containers
**What goes wrong:** Worker crashes mid-job; container keeps running, consuming CPU/RAM, never cleaned up.
**Why it happens:** Celery task exception skips the finally block only if the worker process itself dies.
**How to avoid:** (a) Always use `try/finally` in the task, (b) implement an orphan watchdog Celery beat task that lists containers matching `orfs_job_*`, checks their run IDs against the DB, and stops any whose run is not in `running` state. Build this in Plan 01-03, not later.
**Warning signs:** `docker ps` shows containers running for hours with no corresponding active job.

### Pitfall 5: Docker cgroup v2 on RHEL 9 / Rocky 9
**What goes wrong:** `--memory-swap` and `--cpu-quota` silently ignored or cause container start failure on cgroup v2 systems.
**Why it happens:** The OS (RHEL/Rocky 9 running Linux 5.14+) uses cgroup v2 by default. Docker cgroup v2 support is complete in Docker 20.10+ but some `storage-opt size=` flags require `overlay2` with `pquota` mount option.
**How to avoid:** Verify `docker info | grep Cgroup` returns `cgroup v2`. Test resource limits with a simple container before the first ORFS run. Document `overlay2` + `pquota` requirement in the deployment README.
**Warning signs:** `docker: Error response from daemon: invalid argument` on container start, or jobs exceeding their memory limit without being killed.

### Pitfall 6: boto3 Signature Version with MinIO
**What goes wrong:** Presigned URLs return 403 when client downloads.
**Why it happens:** boto3 defaults to signature v2 in some regions; MinIO requires v4.
**How to avoid:** Always pass `Config(signature_version="s3v4")` to boto3 client constructor.
**Warning signs:** `SignatureDoesNotMatch` in MinIO logs; presigned URL works in dev but not production.

### Pitfall 7: xterm.js Scrollback 0 = Unlimited (but uses browser memory)
**What goes wrong:** Browser tab crashes after multi-hour ORFS run with millions of log lines.
**Why it happens:** ORFS can emit >100k log lines; `scrollback: 0` (unlimited) stores all in browser memory.
**How to avoid:** Set `scrollback: 50000` — enough for full ORFS runs (typical: 5k-30k lines) without OOM risk. Also apply LTRIM on the server side. `scrollback: 0` is a soft "unlimited" that maps to the buffer size, not actually infinite.
**Warning signs:** Browser tab memory climbing; eventual tab crash on long jobs.

### Pitfall 8: VNC Token in URL vs. WebSocket Handshake
**What goes wrong:** Token placed as a query parameter in the WebSocket URL is logged by Nginx access logs.
**Why it happens:** Default Nginx logging includes full URI with query string.
**How to avoid:** Embed the token in the URL path segment (`/vnc/{token}/websockify`) rather than as a query parameter. Nginx `auth_request` validates `/api/v1/vnc/validate` passing the path token. Alternatively, suppress Nginx query logging for VNC paths.
**Warning signs:** VNC tokens visible in Nginx access.log.

---

## Code Examples

### ORFS Metrics Parsing
```python
# Source: https://openroad-flow-scripts.readthedocs.io/en/latest/contrib/Metrics.html
# ORFS generates: logs/PLATFORM/DESIGN/metadata.json (METRICS2.1 format)
import json
from pathlib import Path

def parse_ppa_metrics(workspace: str, platform: str, design: str) -> dict:
    # Primary: metadata.json in the logs directory
    metadata_path = Path(workspace) / "logs" / platform / design / "metadata.json"
    if metadata_path.exists():
        data = json.loads(metadata_path.read_text())
        return {
            "worst_negative_slack": data.get("timing__setup__ws"),
            "total_negative_slack": data.get("timing__setup__tns"),
            "drc_violations": data.get("route__drc_errors__count", 0),
            "core_area": data.get("design__instance__area"),
            "total_power": data.get("power__total"),
            "flow_complete": data.get("flow__platform__status") == "succeeded",
        }
    # Fallback: parse final timing report text
    return parse_final_timing_report(workspace, platform, design)
```

### Stage Transition Detection in Log Streamer
```python
# Regex patterns for ORFS stage boundary lines
import re

STAGE_PATTERNS = {
    "synthesis":   re.compile(r"(Starting|Finished)\s+synthesis", re.IGNORECASE),
    "floorplan":   re.compile(r"(Starting|Finished)\s+floorplan", re.IGNORECASE),
    "place":       re.compile(r"(Starting|Finished)\s+placement", re.IGNORECASE),
    "cts":         re.compile(r"(Starting|Finished)\s+cts", re.IGNORECASE),
    "route":       re.compile(r"(Starting|Finished)\s+routing", re.IGNORECASE),
    "gds":         re.compile(r"(Starting|Finished)\s+final", re.IGNORECASE),
}

SEPARATOR_FMT = "═══ {stage} ══════════════════════════════════"

def detect_stage(line: str) -> str | None:
    for stage, pattern in STAGE_PATTERNS.items():
        if pattern.search(line):
            return stage
    return None
```

**Note:** The exact log output format should be verified against a live ORFS run during development. The patterns above are initial hypotheses based on the ORFS documentation; adjust regexes against actual `make` output.

### Axios Token Refresh Interceptor
```typescript
// Source: axios docs + AUTH-04 requirement
// hooks/useTokenRefresh.ts
import axios from "axios";
import { useStore } from "../store";

let isRefreshing = false;
let failedQueue: Array<{resolve: Function; reject: Function}> = [];

axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) =>
          failedQueue.push({ resolve, reject })
        ).then((token) => {
          original.headers["Authorization"] = `Bearer ${token}`;
          return axiosInstance(original);
        });
      }
      original._retry = true;
      isRefreshing = true;
      try {
        const { data } = await axiosInstance.post("/api/v1/auth/refresh");
        const newToken = data.access_token;
        useStore.getState().setAccessToken(newToken);
        failedQueue.forEach(({ resolve }) => resolve(newToken));
        failedQueue = [];
        original.headers["Authorization"] = `Bearer ${newToken}`;
        return axiosInstance(original);
      } catch (refreshError) {
        failedQueue.forEach(({ reject }) => reject(refreshError));
        failedQueue = [];
        useStore.getState().clearAuth();
        window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| python-jose for JWT | PyJWT 2.10.x | 2024 (python-jose deprecated) | Direct drop-in; simpler API |
| passlib[bcrypt] | argon2-cffi 25.x | 2024 (passlib unmaintained) | Argon2id is stronger; GPU-resistant |
| xterm (no scope) | @xterm/xterm (scoped) | 2023 (v5.0) | Package renamed; all addons now @xterm/* |
| SQLAlchemy 1.x sync | SQLAlchemy 2.0 async | 2023 | `async_sessionmaker`, `AsyncSession` are now stable |
| `python:3.x` Dockerfile | `python:3.12-slim` | 2024 | Python 3.12 has significant performance improvements |
| Pydantic v1 | Pydantic v2 | 2023 | 5-50x faster validation; `model_config` not `Config` class |

**Deprecated/outdated:**
- `python-jose`: Do not use. Unmaintained since 2023. Replace with PyJWT.
- `passlib`: Do not use. No active maintenance. Replace with argon2-cffi.
- `xterm` (unscoped npm package): Use `@xterm/xterm` (scoped). The unscoped package is v3, not maintained.
- Pydantic `orm_mode = True`: Replaced by `model_config = ConfigDict(from_attributes=True)` in Pydantic v2.

---

## Open Questions

1. **ORFS log format for stage boundaries**
   - What we know: ORFS is a Makefile-driven flow; stages emit logging to stdout
   - What's unclear: The exact log line format for stage start/end transitions varies by ORFS version
   - Recommendation: Run a test `gcd` design during infrastructure setup (Plan 01-01) and capture actual log output to calibrate stage detection regexes

2. **KLayout headless mode in Docker**
   - What we know: KLayout Python API `lay.LayoutView` works in headless/batch mode
   - What's unclear: Whether the ORFS Docker image (`openroad/orfs:latest`) includes KLayout or whether a separate KLayout installation is needed in the worker
   - Recommendation: Check `openroad/orfs:latest` image for KLayout availability; if absent, consider a separate worker Dockerfile that adds KLayout, OR run KLayout in a separate container via Docker SDK

3. **cgroup v2 `storage-opt size=` support on host**
   - What we know: The host is RHEL/Rocky 9 (kernel 5.14); cgroup v2 is default
   - What's unclear: Whether Docker on this host is configured with `overlay2` + `pquota` mount option required for `storage-opt size=`
   - Recommendation: Test `docker run --storage-opt size=5G hello-world` on the deployment host in Plan 01-01; if it fails, remove `storage-opt` and rely on disk quota at the filesystem level instead

4. **Nginx auth_request for VNC token validation**
   - What we know: Nginx `auth_request` module can call an internal endpoint before proxying
   - What's unclear: Whether the base Nginx image used in Docker Compose includes `ngx_http_auth_request_module`
   - Recommendation: Use `nginx:alpine` which includes auth_request by default; verify with `nginx -V 2>&1 | grep auth_request`

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | `backend/pytest.ini` — Wave 0 gap |
| Quick run command | `pytest backend/tests/ -x -q --tb=short` |
| Full suite command | `pytest backend/tests/ -v --cov=app --cov-report=term-missing` |
| Frontend framework | Vitest 2.x |
| Frontend run command | `cd frontend && npm test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | POST /auth/register creates user with hashed password | integration | `pytest backend/tests/test_auth.py::test_register -x` | Wave 0 |
| AUTH-02 | POST /auth/login returns JWT + sets httpOnly cookie | integration | `pytest backend/tests/test_auth.py::test_login_returns_jwt_and_cookie -x` | Wave 0 |
| AUTH-03 | POST /auth/logout invalidates refresh token | integration | `pytest backend/tests/test_auth.py::test_logout_invalidates_refresh -x` | Wave 0 |
| AUTH-04 | POST /auth/refresh returns new access token using cookie | integration | `pytest backend/tests/test_auth.py::test_refresh_token -x` | Wave 0 |
| JOB-01 | POST /projects creates project + uploads files to MinIO | integration | `pytest backend/tests/test_jobs.py::test_project_create_and_upload -x` | Wave 0 |
| JOB-02 | ORFS container spawns with cgroup limits and no network | unit (mock Docker) | `pytest backend/tests/test_container.py::test_container_resource_limits -x` | Wave 0 |
| JOB-03 | Log lines published to Redis are delivered via WebSocket | integration | `pytest backend/tests/test_websocket.py::test_log_stream -x` | Wave 0 |
| JOB-04 | Stage transition in log updates run.status in DB | unit | `pytest backend/tests/test_log_parser.py::test_stage_detection -x` | Wave 0 |
| JOB-05 | DELETE /jobs/{id} stops container and sets status cancelled | integration (mock Docker) | `pytest backend/tests/test_jobs.py::test_cancel_job -x` | Wave 0 |
| RSLT-01 | PPA metrics parsed from metadata.json and stored in runs.ppa | unit | `pytest backend/tests/test_metrics.py::test_parse_ppa -x` | Wave 0 |
| RSLT-02 | GET /jobs/{id}/artifacts returns presigned URLs | integration (mock S3) | `pytest backend/tests/test_artifacts.py::test_presigned_urls -x` | Wave 0 |
| RSLT-03 | KLayout PNG generated and uploaded to MinIO on job complete | unit (mock KLayout) | `pytest backend/tests/test_tile_generator.py::test_png_generation -x` | Wave 0 |
| RSLT-04 | GET /projects/{id}/runs returns run history with PPA | integration | `pytest backend/tests/test_projects.py::test_run_history -x` | Wave 0 |
| LAYT-01 | VNC session start returns valid HMAC token | unit | `pytest backend/tests/test_vnc.py::test_vnc_token_creation -x` | Wave 0 |
| DASH-04 | GET /users/me includes storage_used_bytes | integration | `pytest backend/tests/test_users.py::test_storage_usage -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/ -x -q --tb=short` (< 30 seconds with mocked Docker/S3)
- **Per wave merge:** `pytest backend/tests/ -v --cov=app --cov-report=term-missing && cd frontend && npm test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/pytest.ini` — asyncio_mode = "auto", testpaths, markers
- [ ] `backend/tests/conftest.py` — async_engine, session rollback fixture, TestClient, mock_s3, mock_docker, mock_redis fixtures
- [ ] `backend/tests/test_auth.py` — AUTH-01 through AUTH-04
- [ ] `backend/tests/test_jobs.py` — JOB-01, JOB-05
- [ ] `backend/tests/test_container.py` — JOB-02
- [ ] `backend/tests/test_websocket.py` — JOB-03
- [ ] `backend/tests/test_log_parser.py` — JOB-04
- [ ] `backend/tests/test_metrics.py` — RSLT-01
- [ ] `backend/tests/test_artifacts.py` — RSLT-02
- [ ] `backend/tests/test_tile_generator.py` — RSLT-03
- [ ] `backend/tests/test_projects.py` — RSLT-04
- [ ] `backend/tests/test_vnc.py` — LAYT-01
- [ ] `backend/tests/test_users.py` — DASH-04
- [ ] Framework install: `uv add --dev pytest pytest-asyncio anyio httpx moto[s3]` — moto for mock S3/MinIO

---

## Sources

### Primary (HIGH confidence)
- FastAPI official docs (fastapi.tiangolo.com) — JWT auth, async SQLAlchemy, WebSocket, testing
- SQLAlchemy 2.0 async docs — sessionmaker, AsyncSession
- Celery 5.4 docs (docs.celeryq.dev) — queue routing, worker configuration
- Docker SDK for Python 7.1 (docker-py.readthedocs.io) — container run, resource limits
- PyJWT 2.10 (pyjwt.readthedocs.io) — confirmed replacement for python-jose
- argon2-cffi GitHub (github.com/hynek/argon2-cffi) — confirmed current standard
- xterm.js docs + GitHub (xtermjs.org) — addon versions, scrollback, React integration
- boto3 presigned URL docs (boto3.amazonaws.com) — MinIO compatibility, signature v4
- OpenROAD Flow Scripts docs (openroad-flow-scripts.readthedocs.io) — metrics format, METRICS2.1
- KLayout Python API (klayout.de/doc-qt5) — headless PNG export, LayoutView
- Zustand docs (zustand.docs.pmnd.rs) — slices pattern, TypeScript usage

### Secondary (MEDIUM confidence)
- STATE.md project decisions — PyJWT/argon2-cffi decision recorded; GIN vs B-tree index warning
- Multiple 2025-2026 blog posts confirming FastAPI + async SQLAlchemy + Alembic stack
- Redis asyncio pub/sub patterns verified across multiple independent sources

### Tertiary (LOW confidence — flag for validation)
- ORFS stage log format regexes: hypothesized from docs; must verify against live run
- KLayout availability in `openroad/orfs:latest` image: requires image inspection
- cgroup v2 `storage-opt size=` support on deployment host: requires host-level testing

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions cross-referenced against official docs and project STATE.md decisions
- Architecture patterns: HIGH — based on official docs + CONTEXT.md locked decisions
- Pitfalls: HIGH (items 1-6) / MEDIUM (items 7-8) — most verified from official sources or project constraints
- ORFS integration specifics: MEDIUM — docs confirm structure; exact log format requires live validation

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (stable ecosystem; 30 days reasonable)
