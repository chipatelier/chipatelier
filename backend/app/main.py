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

# --- Artifacts routes (plan 01-05) ---
from app.api.routes.artifacts import router as artifacts_router

app.include_router(artifacts_router, prefix="/api/v1")

# --- VNC routes (plan 01-06) ---
from app.api.routes.vnc import router as vnc_router

app.include_router(vnc_router, prefix="/api/v1")

# --- AI routes (plan 01-07) — stub returns 501 until Phase 3 wires Ollama ---
from app.api.routes.ai import router as ai_router

app.include_router(ai_router, prefix="/api/v1")
