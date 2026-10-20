"""
Institution model — an educational institution involved in one or more complaints.

Design notes
------------
* aicte_institution_id is nullable because some institutions arrive via
  complaint submissions before they are registered with AICTE.
* The unique constraint on aicte_institution_id uses a partial index
  (WHERE aicte_institution_id IS NOT NULL) so multiple NULL values are
  permitted — standard SQL unique constraints treat each NULL as distinct,
  but an explicit partial index is clearer in intent and portable.
* normalized_name is a pre-computed lowercased/stripped version of name,
  used for fast fuzzy-match lookups without depending on a full-text engine.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin


class Institution(Base, TimestampMixin):
    """An educational institution referenced in complaint cases."""

    __tablename__ = "institutions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="UUID primary key.",
    )
    aicte_institution_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment=(
            "External AICTE institution identifier when known. "
            "Unique across non-null values (enforced via partial index)."
        ),
    )
    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Official institution name as received.",
    )
    normalized_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Lowercase, whitespace-normalised version of name for fast matching.",
    )
    institution_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="E.g. 'university', 'college', 'polytechnic'.",
    )
    state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Indian state / union territory.",
    )
    district: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    cases: Mapped[list["ComplaintCase"]] = relationship(  # type: ignore[name-defined]
        "ComplaintCase",
        back_populates="institution",
        # Do NOT cascade delete — complaints outlive institution records.
        passive_deletes=True,
    )

    # ------------------------------------------------------------------ #
    # Constraints and indexes
    # ------------------------------------------------------------------ #
    __table_args__ = (
        # Partial unique index: aicte_institution_id must be unique among
        # non-null values, but multiple NULLs are allowed.
        Index(
            "uq_institutions_aicte_id_notnull",
            "aicte_institution_id",
            unique=True,
            postgresql_where=text("aicte_institution_id IS NOT NULL"),
        ),
        Index("ix_institutions_normalized_name", "normalized_name"),
        Index("ix_institutions_state_district", "state", "district"),
    )

    def __repr__(self) -> str:
        return (
            f"<Institution id={self.id!r} name={self.name!r} "
            f"aicte_id={self.aicte_institution_id!r}>"
        )
