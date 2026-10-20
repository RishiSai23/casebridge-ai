"""
CaseRelationship model — a proposed or confirmed link between two cases.

Design: directed edge with duplicate-pair prevention
------------------------------------------------------
The relationship is stored as a directed edge (source_case_id → target_case_id)
but treated as unordered for uniqueness purposes.

Preventing duplicate pairs
--------------------------
A partial unique index enforces that a given (source, target, type) triple
appears at most once regardless of direction:

    UNIQUE (source_case_id, target_case_id, relationship_type)
    with CHECK (source_case_id < target_case_id)

The application layer MUST normalise the pair so that the lexicographically
smaller UUID is always stored as source_case_id.  This is enforced by a
CHECK constraint that prevents source >= target.  Alembic renders this as
a column-level check.

Self-relationship prevention
-----------------------------
A separate CHECK constraint prevents a case from relating to itself:
    CHECK (source_case_id != target_case_id)

Human-review requirement
-------------------------
No code path should change status from 'potential' to 'confirmed' or
'dismissed' automatically.  The confidence_score is evidence for a human
reviewer; it is never used by the system to autonomously confirm a link.

confidence_score
-----------------
Stored as NUMERIC(4,3) — 4 significant digits, 3 decimal places — allowing
values from 0.000 to 1.000.  A database-level check enforces this range.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin
from app.db.models.enums import RelationshipStatus, RelationshipType


class CaseRelationship(Base, TimestampMixin):
    """A possible or confirmed relationship between two complaint cases."""

    __tablename__ = "case_relationships"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    source_case_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("complaint_cases.id", ondelete="RESTRICT"),
        nullable=False,
        comment=(
            "Lexicographically smaller UUID of the pair. "
            "Application MUST normalise the order before insert."
        ),
    )
    target_case_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("complaint_cases.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Lexicographically larger UUID of the pair.",
    )
    relationship_type: Mapped[RelationshipType] = mapped_column(
        SAEnum(
            RelationshipType,
            name="relationship_type",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        comment=(
            "Nature of the link: same_institution | similar_subject | "
            "repeated_complaint | coordinated_action | evidence_shared."
        ),
    )
    status: Mapped[RelationshipStatus] = mapped_column(
        SAEnum(
            RelationshipStatus,
            name="relationship_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=RelationshipStatus.POTENTIAL,
        comment="potential | confirmed | dismissed. Changed only by human reviewers.",
    )
    confidence_score: Mapped[float | None] = mapped_column(
        Numeric(4, 3),
        nullable=True,
        comment=(
            "System-computed similarity score in [0.000, 1.000]. "
            "For human reference only — never triggers automatic confirmation."
        ),
    )
    evidence: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Structured explanation of the signals that produced this relationship. "
            "E.g. {\"signals\": [{\"type\": \"subject_overlap\", \"score\": 0.87}]}. "
            "Must not contain sensitive personal data."
        ),
    )
    reviewed_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who last reviewed this relationship.",
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the most recent review action occurred (UTC).",
    )

    # ------------------------------------------------------------------ #
    # Relationships (ORM)
    # ------------------------------------------------------------------ #
    source_case: Mapped["ComplaintCase"] = relationship(  # type: ignore[name-defined]
        "ComplaintCase",
        back_populates="outgoing_relationships",
        foreign_keys=[source_case_id],
    )
    target_case: Mapped["ComplaintCase"] = relationship(  # type: ignore[name-defined]
        "ComplaintCase",
        back_populates="incoming_relationships",
        foreign_keys=[target_case_id],
    )
    reviewer: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        "User",
        back_populates="case_relationship_reviews",
        foreign_keys=[reviewed_by],
    )

    # ------------------------------------------------------------------ #
    # Constraints and indexes
    # ------------------------------------------------------------------ #
    __table_args__ = (
        # Prevent self-relationships
        CheckConstraint(
            "source_case_id != target_case_id",
            name="ck_case_relationships_no_self",
        ),
        # Enforce canonical ordering (source < target) to prevent
        # (A→B) and (B→A) duplicate representations of the same pair.
        CheckConstraint(
            "source_case_id < target_case_id",
            name="ck_case_relationships_canonical_order",
        ),
        # Prevent duplicate (source, target, type) triples.
        UniqueConstraint(
            "source_case_id",
            "target_case_id",
            "relationship_type",
            name="uq_case_relationships_pair_type",
        ),
        # Score must be in [0, 1] when present.
        CheckConstraint(
            "confidence_score IS NULL OR "
            "(confidence_score >= 0.000 AND confidence_score <= 1.000)",
            name="ck_case_relationships_score_range",
        ),
        Index("ix_case_relationships_source", "source_case_id"),
        Index("ix_case_relationships_target", "target_case_id"),
        Index("ix_case_relationships_status", "status"),
        Index("ix_case_relationships_type", "relationship_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<CaseRelationship {self.source_case_id!r}→{self.target_case_id!r} "
            f"type={self.relationship_type!r} status={self.status!r}>"
        )
