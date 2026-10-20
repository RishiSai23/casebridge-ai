"""
Database engine and session factory.

The engine is created lazily — calling get_engine() or get_db() for the
first time creates the engine.  The FastAPI application imports this module
at startup but does NOT call get_engine() unless a route or dependency
explicitly requests a session.

This means the application starts cleanly even when DATABASE_URL is empty
(e.g. during local health-check-only development), and the readiness probe
at /api/v1/health/ready correctly reports 'degraded' until the database is
configured and reachable.

Usage in route dependencies
---------------------------
    from app.db.session import get_db
    from sqlalchemy.ext.asyncio import AsyncSession

    async def my_route(db: AsyncSession = Depends(get_db)):
        ...

Engine configuration
--------------------
* pool_pre_ping=True  — validates connections before use; avoids stale
  connection errors after a database restart.
* echo is controlled by APP_ENV; SQL logging is enabled only in development.
* pool_size / max_overflow defaults are suitable for a single-process
  Uvicorn deployment; tune these for production via env vars (future task).
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

# Module-level singletons — initialised on first call to get_engine().
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the singleton async engine, creating it on first call.

    Raises
    ------
    ValueError
        If DATABASE_URL is not configured in the application settings.
    """
    global _engine, _session_factory  # noqa: PLW0603

    if _engine is not None:
        return _engine

    settings = get_settings()
    if not settings.DATABASE_URL:
        raise ValueError(
            "DATABASE_URL is not configured. "
            "Set it in your .env file before using database operations."
        )

    _engine = create_async_engine(
        settings.DATABASE_URL,
        echo=(settings.APP_ENV == "development"),
        pool_pre_ping=True,
        # Future: expose pool_size / max_overflow via Settings.
    )
    _session_factory = async_sessionmaker(
        _engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    return _engine


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields one AsyncSession per request.

    The session is automatically closed when the request completes or when
    an exception propagates.  Commit must be called explicitly inside the
    route handler — the dependency does not auto-commit.

    Example
    -------
        from fastapi import Depends
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.db.session import get_db

        @router.post("/items")
        async def create_item(db: AsyncSession = Depends(get_db)):
            ...
            await db.commit()
    """
    get_engine()  # ensures _session_factory is initialised; raises if URL missing

    assert _session_factory is not None  # guaranteed by get_engine()
    async with _session_factory() as session:
        yield session
