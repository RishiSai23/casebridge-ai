"""
User model — platform users (staff, bureau officers, analysts).

This is NOT a public complainant record.  Complainant identity is outside
the scope of the current platform design.

Authentication, password storage and login endpoints are deferred to a
future task.  This model stores only the minimum information needed to
associate actions and assignments with a named actor.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import Boolean, Enum as SAEnum, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin
from app.db.models.enums import UserRole


class User(Base, TimestampMixin):
    """A platform staff member or bureau officer."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="UUID primary key.",
    )
    display_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Human-readable name shown in the UI.",
    )
    email: Mapped[str] = mapped_column(
        String(320),  # RFC 5321 maximum
        nullable=False,
        unique=True,
        comment="Unique email address used for identification.",
    )
    role: Mapped[UserRole] = mapped_column(
        SAEnum(
            UserRole,
            name="user_role",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=UserRole.VIEWER,
        comment="Platform role: admin | bureau_officer | analyst | viewer.",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="False means the account is disabled; the row is retained for audit continuity.",
    )

    # ------------------------------------------------------------------ #
    # Relationships (back-references only — forward refs declared in children)
    # ------------------------------------------------------------------ #
    case_events: Mapped[list["CaseEvent"]] = relationship(  # type: ignore[name-defined]
        "CaseEvent", back_populates="actor", foreign_keys="CaseEvent.actor_user_id"
    )
    case_assignments_created: Mapped[list["CaseAssignment"]] = relationship(  # type: ignore[name-defined]
        "CaseAssignment",
        back_populates="assigned_by_user",
        foreign_keys="CaseAssignment.assigned_by",
    )
    case_relationship_reviews: Mapped[list["CaseRelationship"]] = relationship(  # type: ignore[name-defined]
        "CaseRelationship",
        back_populates="reviewer",
        foreign_keys="CaseRelationship.reviewed_by",
    )
    coordination_actions_assigned: Mapped[list["CoordinationAction"]] = relationship(  # type: ignore[name-defined]
        "CoordinationAction",
        back_populates="assignee",
        foreign_keys="CoordinationAction.assigned_to",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(  # type: ignore[name-defined]
        "AuditLog", back_populates="actor", foreign_keys="AuditLog.actor_user_id"
    )

    # ------------------------------------------------------------------ #
    # Indexes
    # ------------------------------------------------------------------ #
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_role_active", "role", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} email={self.email!r} role={self.role!r}>"
