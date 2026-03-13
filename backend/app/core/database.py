"""PostgreSQL async database connection using SQLAlchemy 2.0."""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency: yield an async DB session, ensure it's closed after."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create all tables (dev convenience; Alembic handles production migrations)."""
    from app.models.base import Base  # noqa: F401
    import app.models  # noqa: F401 — ensure all models registered

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
