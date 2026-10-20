"""
Alembic migration environment.

This file is executed by Alembic for both 'offline' (SQL-generation) and
'online' (live database) migration modes.

Key responsibilities
--------------------
1. Read DATABASE_URL from environment / .env file (never from alembic.ini).
2. Import all model modules so SQLAlchemy metadata is fully populated before
   autogenerate inspects it.
3. Configure the migration context with the target metadata.

Async engine note
-----------------
The application uses an asyncpg driver (postgresql+asyncpg://...).
Alembic's run_migrations_online() is an async function that uses
AsyncEngine.begin() so it is compatible with the asyncpg driver.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# --------------------------------------------------------------------------- #
# Import all models to populate Base.metadata
# --------------------------------------------------------------------------- #
# This single import triggers the models package __init__.py which imports
# every model module.  Alembic autogenerate then sees the complete schema.
import app.db.models  # noqa: F401 — side-effect import for metadata discovery
from app.db.models.base import Base

# --------------------------------------------------------------------------- #
# Alembic config object
# --------------------------------------------------------------------------- #
config = context.config

# Interpret the config file for Python logging if present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata Alembic uses for autogenerate comparisons.
target_metadata = Base.metadata

# --------------------------------------------------------------------------- #
# Database URL — read from environment, not from alembic.ini
# --------------------------------------------------------------------------- #
def _get_database_url() -> str:
    """Return DATABASE_URL from environment or .env file.

    Tries, in order:
    1. DATABASE_URL environment variable (already exported)
    2. The application's Settings object (reads .env file if present)

    Raises
    ------
    RuntimeError
        If DATABASE_URL is not configured.
    """
    # Prefer an already-exported env var (CI, production).
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url

    # Fall back to pydantic-settings (reads .env).
    try:
        from app.core.config import get_settings
        url = get_settings().DATABASE_URL.strip()
    except Exception:
        pass

    if not url:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Export it as an environment variable or add it to .env before "
            "running Alembic migrations."
        )
    return url


# --------------------------------------------------------------------------- #
# Offline migrations (generates SQL without a live connection)
# --------------------------------------------------------------------------- #
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    In offline mode, Alembic generates SQL statements and writes them to
    stdout (or a file) without connecting to a database.  Useful for
    reviewing migration SQL before applying it.

    Run with:
        alembic upgrade head --sql
    """
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Render server defaults so the generated SQL matches the ORM models.
        render_as_batch=False,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# --------------------------------------------------------------------------- #
# Online migrations (connects to the live database)
# --------------------------------------------------------------------------- #
async def run_migrations_online() -> None:
    """Run migrations in 'online' mode (requires a live database connection).

    Run with:
        alembic upgrade head
    """
    url = _get_database_url()
    connectable = create_async_engine(url, echo=False)

    async with connectable.begin() as conn:
        await conn.run_sync(_run_sync_migrations)

    await connectable.dispose()


def _run_sync_migrations(sync_conn: object) -> None:
    context.configure(
        connection=sync_conn,  # type: ignore[arg-type]
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
