"""
CaseEvent model — append-only history of significant case activity.

Design: event sourcing (append-only)
-------------------------------------
Events are never modified or deleted.  Every state transition, note, or
assignment action should produce an event row.  This gives a complete,
tamper-evident timeline for each case.

The 'metadata' JSON column stores additional structured context relevant to
the event type (e.g. old/new status values for STATUS_CHANGED, or a list of
evidence IDs for EVIDENCE_RECEIVED).  Do not store sensitive personal data
or credentials in this field.

event_type values are defined in app.db.models.enums.CaseEventType.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base
from app.db.models.enums import CaseEventType


class CaseEvent(Base):
    """An immutable record of a significant event in a case's lifecycle."""

    __tablename__ = "case_events"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    case_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("complaint_cases.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The case this event belongs to.",
    )
    event_type: Mapped[CaseEventType] = mapped_column(
        SAEnum(
            CaseEventType,
            name="case_event_type",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        comment=(
            "Event classification: created | status_changed | priority_changed | "
            "assigned | transferred | note_added | evidence_requested | "
            "evidence_received | relationship_flagged | coordination_initiated | "
            "closed | withdrawn."
        ),
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable summary of what happened.",
    )
    actor_user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who triggered this event. NULL for system-generated events.",
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the event occurred (UTC). Set explicitly, not a server default.",
    )
    event_metadata: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        comment=(
            "Optional structured context for this event type. "
            "Must not contain credentials, passwords, or sensitive PII."
        ),
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    case: Mapped["ComplaintCase"] = relationship(  # type: ignore[name-defined]
        "ComplaintCase", back_populates="events"
    )
    actor: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        "User",
        back_populates="case_events",
        foreign_keys=[actor_user_id],
    )

    # ------------------------------------------------------------------ #
    # Indexes
    # ------------------------------------------------------------------ #
    __table_args__ = (
        Index("ix_case_events_case_id", "case_id"),
        Index("ix_case_events_occurred_at", "occurred_at"),
        Index("ix_case_events_event_type", "event_type"),
        # Common query: all events for a case, chronologically
        Index("ix_case_events_case_occurred", "case_id", "occurred_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<CaseEvent case={self.case_id!r} "
            f"type={self.event_type!r} at={self.occurred_at!r}>"
        )
