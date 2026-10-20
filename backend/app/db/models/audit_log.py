"""
AuditLog model — structured record of significant administrative changes.

Design principles
------------------
* Append-only: rows are never updated or deleted.
* actor_user_id is nullable to support system-initiated actions (e.g. automated
  status transitions triggered by a scheduler).
* entity_type + entity_id form a polymorphic reference — no foreign-key
  constraint is used so that audit records survive entity deletion.
* details is a JSON field for relevant, non-sensitive audit metadata.
  It MUST NOT contain passwords, secrets, full complaint text, or PII beyond
  what is strictly necessary for the audit purpose.

Intended audit actions (illustrative, not exhaustive):
  case.created, case.status_changed, case.closed
  assignment.created, assignment.transferred
  relationship.confirmed, relationship.dismissed
  coordination.created, coordination.completed
  user.created, user.deactivated
  bureau.created, bureau.deactivated
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base


class AuditLog(Base):
    """An immutable record of an administrative or workflow event."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    actor_user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who performed the action. NULL for system-initiated actions.",
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Machine-readable action identifier (e.g. 'case.status_changed').",
    )
    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Type of the entity affected (e.g. 'ComplaintCase', 'Bureau').",
    )
    entity_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment=(
            "Primary key of the affected entity as a string. "
            "No FK constraint — records must survive entity deletion."
        ),
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="UTC timestamp of the action.",
    )
    details: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Structured audit context. Must not contain credentials, secrets, "
            "or unrestricted copies of sensitive documents."
        ),
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    actor: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        "User",
        back_populates="audit_logs",
        foreign_keys=[actor_user_id],
    )

    # ------------------------------------------------------------------ #
    # Indexes
    # ------------------------------------------------------------------ #
    __table_args__ = (
        Index("ix_audit_logs_actor_user_id", "actor_user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_occurred_at", "occurred_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog action={self.action!r} "
            f"entity={self.entity_type!r}:{self.entity_id!r} "
            f"at={self.occurred_at!r}>"
        )
