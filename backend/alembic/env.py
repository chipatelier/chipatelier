"""Alembic environment configuration — async pattern for asyncpg."""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

# Alembic Config object — provides access to .ini file values
config = context.config

# Interpret the config file for Python logging, if present
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so metadata is fully populated
from app.models.base import Base
import app.models  # noqa: F401 — ensures all model classes are registered

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without connecting)."""
    from app.core.config import get_settings
    url = get_settings().DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine (required for asyncpg)."""
    from app.core.config import get_settings
    connectable = create_async_engine(get_settings().DATABASE_URL)

    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)

    await connectable.dispose()


def _do_run_migrations(connection: AsyncConnection) -> None:
    """Execute the Alembic migration context synchronously (called via run_sync)."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Entry point for online migration mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
