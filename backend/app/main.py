"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import get_settings
from app.core.database import init_db
from app.core.redis import close_redis, get_redis

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize DB and storage on startup."""
    await init_db()
    _ensure_storage_bucket()
    yield
    await close_redis()


def _ensure_storage_bucket() -> None:
    """Create the MinIO artifacts bucket if it doesn't exist.

    Runs synchronously at startup — bucket creation is instantaneous and
    only does work on first boot or after a MinIO data wipe.
    """
    import logging
    import boto3
    from botocore.exceptions import ClientError

    log = logging.getLogger("chipatelier.startup")
    try:
        client = boto3.client(
            "s3",
            endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
        )
        try:
            client.head_bucket(Bucket=settings.S3_BUCKET_ARTIFACTS)
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchBucket"):
                client.create_bucket(Bucket=settings.S3_BUCKET_ARTIFACTS)
                log.info("Created MinIO bucket: %s", settings.S3_BUCKET_ARTIFACTS)
    except Exception as exc:
        logging.getLogger("chipatelier.startup").warning(
            "Could not ensure storage bucket (MinIO may not be ready yet): %s", exc
        )


app = FastAPI(
    title="ChipAtelier API",
    description="RTL-to-GDS ASIC implementation platform for university students",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.get("/healthz", tags=["health"])
async def healthz() -> dict[str, str]:
    """Health check — verifies DB and Redis connectivity."""
    db_status = "error"
    redis_status = "error"
    http_status = status.HTTP_200_OK

    # Check DB
    try:
        from sqlalchemy import text
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    # Check Redis
    try:
        redis = await get_redis()
        await redis.ping()
        redis_status = "ok"
    except Exception:
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=http_status,
        content={"status": "ok" if http_status == 200 else "degraded", "db": db_status, "redis": redis_status},
    )


# --- Authentication and user routes ---
from app.api.routes import auth as auth_routes
from app.api.routes import users as users_routes
from app.api.routes.projects import router as projects_router
from app.api.routes.jobs import router as jobs_router
from app.api.websocket import router as ws_router

app.include_router(auth_routes.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users_routes.router, prefix="/api/v1/users", tags=["users"])
app.include_router(projects_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1/ws", tags=["websocket"])

# --- Prometheus metrics ---
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# --- Artifacts routes (plan 01-05) ---
from app.api.routes.artifacts import router as artifacts_router

app.include_router(artifacts_router, prefix="/api/v1")

# --- VNC routes (plan 01-06) ---
from app.api.routes.vnc import router as vnc_router

app.include_router(vnc_router, prefix="/api/v1")

# --- AI routes (plan 01-07) — stub returns 501 until Phase 3 wires Ollama ---
from app.api.routes.ai import router as ai_router

app.include_router(ai_router, prefix="/api/v1")

# --- Course and assignment routes (plan 02-02) ---
from app.api.routes.courses import router as courses_router
from app.api.routes.assignments import router as assignments_router

app.include_router(courses_router, prefix="/api/v1", tags=["courses"])
app.include_router(assignments_router, prefix="/api/v1", tags=["assignments"])

# --- Submission + auto-grading routes (plan 02-04) ---
from app.api.routes.submissions import router as submissions_router

app.include_router(submissions_router, prefix="/api/v1", tags=["submissions"])

# --- Click-to-inspect query routes (plan 02-05) ---
from app.api.routes.query import router as query_router

app.include_router(query_router, prefix="/api/v1", tags=["query"])
