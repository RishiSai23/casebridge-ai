"""
CaseAssignment model — which bureau owns a case and assignment history.

Design: history-preserving transfers
-------------------------------------
When a case is transferred from Bureau A to Bureau B:
  1. The existing 'active' assignment for Bureau A is updated:
       assignment_status = 'transferred', unassigned_at = now()
  2. A new assignment row is inserted for Bureau B:
       assignment_status = 'active', assigned_at = now()

This means every bureau that ever handled a case is visible in the table.
The "current owner" is the row where assignment_status = 'active' and
unassigned_at IS NULL.

Duplicate active assignment prevention
---------------------------------------
A partial unique index enforces that a case has at most one active,
unassigned assignment at any time:
    UNIQUE (case_id) WHERE assignment_status = 'active' AND unassigned_at IS NULL
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin
from app.db.models.enums import AssignmentStatus


class CaseAssignment(Base, TimestampMixin):
    """Records which bureau handles a case, including full transfer history."""

    __tablename__ = "case_assignments"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    case_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("complaint_cases.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The complaint case being assigned.",
    )
    bureau_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("bureaus.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The bureau taking ownership.",
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When this assignment became effective (UTC).",
    )
    unassigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this assignment ended (transfer or completion). NULL = still active.",
    )
    assignment_status: Mapped[AssignmentStatus] = mapped_column(
        SAEnum(
            AssignmentStatus,
            name="assignment_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=AssignmentStatus.ACTIVE,
        comment="active | transferred | completed",
    )
    assigned_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who created this assignment record (optional).",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Free-text notes recorded at assignment or transfer time.",
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    case: Mapped["ComplaintCase"] = relationship(  # type: ignore[name-defined]
        "ComplaintCase", back_populates="assignments"
    )
    bureau: Mapped["Bureau"] = relationship(  # type: ignore[name-defined]
        "Bureau", back_populates="assignments"
    )
    assigned_by_user: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        "User",
        back_populates="case_assignments_created",
        foreign_keys=[assigned_by],
    )

    # ------------------------------------------------------------------ #
    # Constraints and indexes
    # ------------------------------------------------------------------ #
    __table_args__ = (
        # Enforce at most one active, un-closed assignment per case.
        # This is a partial unique index: only rows where the assignment
        # is still active and not yet unassigned qualify.
        Index(
            "uq_case_assignments_one_active",
            "case_id",
            unique=True,
            postgresql_where=text("assignment_status = 'active' AND unassigned_at IS NULL"),
        ),
        Index("ix_case_assignments_case_id", "case_id"),
        Index("ix_case_assignments_bureau_id", "bureau_id"),
        Index("ix_case_assignments_status", "assignment_status"),
    )

    def __repr__(self) -> str:
        return (
            f"<CaseAssignment case={self.case_id!r} "
            f"bureau={self.bureau_id!r} status={self.assignment_status!r}>"
        )
