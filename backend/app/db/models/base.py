"""
Shared declarative base and common mixin for all ORM models.

All models must inherit from Base (for table mapping) and TimestampMixin
(for created_at / updated_at).  Keeping these in one place ensures that
every table has identical timestamp semantics and that Alembic's metadata
object covers the entire schema.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 2.x declarative base shared by all domain models."""
    pass


class TimestampMixin:
    """Adds created_at and updated_at columns to any model that inherits it.

    Both columns are stored in UTC.

    created_at  — set once by the database at INSERT time and never modified.
    updated_at  — automatically refreshed by the database on every UPDATE.

    Using server_default / onupdate with func.now() means the timestamps are
    set by PostgreSQL, not by the Python process, which avoids clock-skew
    issues in distributed deployments.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="UTC timestamp set by the database at row creation.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="UTC timestamp refreshed by the database on every update.",
    )
