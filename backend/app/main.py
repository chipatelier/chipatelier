"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import init_db
from app.core.redis import close_redis, get_redis

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize DB on startup, close Redis on shutdown."""
    await init_db()
    yield
    await close_redis()


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


# --- Route stubs (implemented in subsequent plans) ---
from fastapi import APIRouter

_auth_router = APIRouter(prefix="/auth", tags=["auth"])
_jobs_router = APIRouter(prefix="/jobs", tags=["jobs"])
_projects_router = APIRouter(prefix="/projects", tags=["projects"])
_artifacts_router = APIRouter(prefix="/artifacts", tags=["artifacts"])
_vnc_router = APIRouter(prefix="/vnc", tags=["vnc"])

app.include_router(_auth_router, prefix="/api/v1")
app.include_router(_jobs_router, prefix="/api/v1")
app.include_router(_projects_router, prefix="/api/v1")
app.include_router(_artifacts_router, prefix="/api/v1")
app.include_router(_vnc_router, prefix="/api/v1")
