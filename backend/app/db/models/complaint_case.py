"""
ComplaintCase model — one complaint filing, tracked independently.

Design notes
------------
* Each row represents a single complaint, not an institution's history.
  One institution may have many cases.
* case_reference is a human-readable, unique reference number (e.g.
  "AICTE-PGRS-2026-001234") assigned at intake.
* priority and status use the string enum values from app.db.models.enums.
  Storing as VARCHAR (not as a PostgreSQL native ENUM type) avoids requiring
  an ALTER TYPE migration every time a new value is added.
* Timestamps use DateTime(timezone=True) with UTC server defaults.
* received_at records when the platform received the complaint (may differ
  from the original filing date if complaints are imported in batch).
* due_at and closed_at are nullable; closed_at is set only on terminal states.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin
from app.db.models.enums import CasePriority, CaseStatus


class ComplaintCase(Base, TimestampMixin):
    """A single complaint case filed against or concerning an institution."""

    __tablename__ = "complaint_cases"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="UUID primary key.",
    )
    case_reference: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="Human-readable unique reference (e.g. 'AICTE-PGRS-2026-001234').",
    )
    institution_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The institution this complaint concerns.",
    )
    subject: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Short subject line of the complaint.",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Full complaint description. May be lengthy.",
    )
    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Optional complaint category (e.g. 'fee_refund', 'infrastructure').",
    )
    priority: Mapped[CasePriority] = mapped_column(
        SAEnum(
            CasePriority,
            name="case_priority",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=CasePriority.MEDIUM,
        comment="Priority: low | medium | high | critical.",
    )
    status: Mapped[CaseStatus] = mapped_column(
        SAEnum(
            CaseStatus,
            name="case_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=CaseStatus.OPEN,
        comment=(
            "Case status: open | under_review | pending_info | "
            "escalated | resolved | closed | withdrawn."
        ),
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the complaint was received by the platform (UTC).",
    )
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Resolution deadline (UTC). Null if not yet set.",
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the case reached a terminal status (closed / withdrawn). UTC.",
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    institution: Mapped["Institution"] = relationship(  # type: ignore[name-defined]
        "Institution", back_populates="cases"
    )
    assignments: Mapped[list["CaseAssignment"]] = relationship(  # type: ignore[name-defined]
        "CaseAssignment",
        back_populates="case",
        # Assignments are preserved on case deletion (not cascaded).
        passive_deletes=True,
    )
    events: Mapped[list["CaseEvent"]] = relationship(  # type: ignore[name-defined]
        "CaseEvent",
        back_populates="case",
        order_by="CaseEvent.occurred_at",
        passive_deletes=True,
    )
    # Relationships where this case is the source
    outgoing_relationships: Mapped[list["CaseRelationship"]] = relationship(  # type: ignore[name-defined]
        "CaseRelationship",
        back_populates="source_case",
        foreign_keys="CaseRelationship.source_case_id",
        passive_deletes=True,
    )
    # Relationships where this case is the target
    incoming_relationships: Mapped[list["CaseRelationship"]] = relationship(  # type: ignore[name-defined]
        "CaseRelationship",
        back_populates="target_case",
        foreign_keys="CaseRelationship.target_case_id",
        passive_deletes=True,
    )
    coordination_actions: Mapped[list["CoordinationAction"]] = relationship(  # type: ignore[name-defined]
        "CoordinationAction",
        back_populates="case",
        foreign_keys="CoordinationAction.case_id",
        passive_deletes=True,
    )
    related_coordination_actions: Mapped[list["CoordinationAction"]] = relationship(  # type: ignore[name-defined]
        "CoordinationAction",
        back_populates="related_case",
        foreign_keys="CoordinationAction.related_case_id",
        passive_deletes=True,
    )

    # ------------------------------------------------------------------ #
    # Indexes
    # ------------------------------------------------------------------ #
    __table_args__ = (
        Index("ix_complaint_cases_case_reference", "case_reference"),
        Index("ix_complaint_cases_institution_id", "institution_id"),
        Index("ix_complaint_cases_status", "status"),
        Index("ix_complaint_cases_priority", "priority"),
        Index("ix_complaint_cases_due_at", "due_at"),
        Index("ix_complaint_cases_received_at", "received_at"),
        # Composite: fast lookup of open/escalated cases by institution
        Index("ix_complaint_cases_institution_status", "institution_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<ComplaintCase ref={self.case_reference!r} "
            f"status={self.status!r} priority={self.priority!r}>"
        )
