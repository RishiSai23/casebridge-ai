"""
CoordinationAction model — a work item requiring cross-bureau coordination.

A CoordinationAction links one primary case (and optionally a related case)
to a specific coordination task.  Actions are created by bureau officers or
(in a future task) proposed by the AI matching engine, but always require
explicit human assignment and completion.

No automated merging or closing of cases is performed based on these records.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin
from app.db.models.enums import CoordinationActionType, CoordinationStatus


class CoordinationAction(Base, TimestampMixin):
    """A coordination task associated with one or more complaint cases."""

    __tablename__ = "coordination_actions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    case_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("complaint_cases.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Primary case this action addresses.",
    )
    related_case_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("complaint_cases.id", ondelete="SET NULL"),
        nullable=True,
        comment="Optional secondary case involved in this coordination (e.g. suspected duplicate).",
    )
    action_type: Mapped[CoordinationActionType] = mapped_column(
        SAEnum(
            CoordinationActionType,
            name="coordination_action_type",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        comment=(
            "Type: review_overlap | follow_up_transfer | "
            "joint_investigation | evidence_consolidation | escalation_review."
        ),
    )
    title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Brief task title shown in coordination queues.",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description of the coordination work required.",
    )
    status: Mapped[CoordinationStatus] = mapped_column(
        SAEnum(
            CoordinationStatus,
            name="coordination_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=CoordinationStatus.PENDING,
        comment="pending | in_progress | completed | cancelled.",
    )
    assigned_to: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User responsible for completing this action.",
    )
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Target completion deadline (UTC).",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the action was completed or cancelled (UTC).",
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    case: Mapped["ComplaintCase"] = relationship(  # type: ignore[name-defined]
        "ComplaintCase",
        back_populates="coordination_actions",
        foreign_keys=[case_id],
    )
    related_case: Mapped["ComplaintCase | None"] = relationship(  # type: ignore[name-defined]
        "ComplaintCase",
        back_populates="related_coordination_actions",
        foreign_keys=[related_case_id],
    )
    assignee: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        "User",
        back_populates="coordination_actions_assigned",
        foreign_keys=[assigned_to],
    )

    # ------------------------------------------------------------------ #
    # Indexes
    # ------------------------------------------------------------------ #
    __table_args__ = (
        Index("ix_coordination_actions_case_id", "case_id"),
        Index("ix_coordination_actions_related_case_id", "related_case_id"),
        Index("ix_coordination_actions_status", "status"),
        Index("ix_coordination_actions_assigned_to", "assigned_to"),
        Index("ix_coordination_actions_due_at", "due_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<CoordinationAction case={self.case_id!r} "
            f"type={self.action_type!r} status={self.status!r}>"
        )
