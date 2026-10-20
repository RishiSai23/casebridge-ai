"""
Bureau model — an AICTE bureau or cell that handles complaints.

Each bureau has a stable machine-readable code (e.g. "PGRS", "LEGAL")
used in routing logic and assignment records.  The human-readable name
may change over time; the code must not.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin


class Bureau(Base, TimestampMixin):
    """An AICTE bureau or cell that receives and processes complaint cases."""

    __tablename__ = "bureaus"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="UUID primary key.",
    )
    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        comment="Stable, uppercase machine-readable code (e.g. 'PGRS', 'LEGAL').",
    )
    name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Full human-readable bureau name.",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description of the bureau's mandate and scope.",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Inactive bureaus are hidden from assignment UIs but retained for history.",
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    assignments: Mapped[list["CaseAssignment"]] = relationship(  # type: ignore[name-defined]
        "CaseAssignment",
        back_populates="bureau",
        passive_deletes=True,
    )

    # ------------------------------------------------------------------ #
    # Indexes
    # ------------------------------------------------------------------ #
    __table_args__ = (
        Index("ix_bureaus_code", "code"),
        Index("ix_bureaus_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Bureau code={self.code!r} name={self.name!r} active={self.is_active}>"
