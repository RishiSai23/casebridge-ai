"""
Pydantic v2 schemas for CaseRelationship.

Important: the API layer must enforce the canonical ordering rule before
calling the service layer.  When a caller supplies (case_a_id, case_b_id),
the service must store min(a,b) as source_case_id and max(a,b) as target_case_id.

The confidence_score is a read-only, system-computed value and must NOT
be accepted in create or update payloads.  Status transitions from 'potential'
to 'confirmed' or 'dismissed' require an explicit review action (future endpoint).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.models.enums import RelationshipStatus, RelationshipType


class CaseRelationshipBase(BaseModel):
    relationship_type: RelationshipType = Field(
        description=(
            "same_institution | similar_subject | repeated_complaint | "
            "coordinated_action | evidence_shared"
        ),
    )


class CaseRelationshipCreate(CaseRelationshipBase):
    """Payload for proposing a new case relationship.

    The caller supplies both case IDs in any order.  The service layer
    normalises them so source < target before persisting.

    confidence_score and evidence are NOT accepted at creation time when
    submitted via the API; they are populated by the AI matching service.
    """

    model_config = ConfigDict(extra="forbid")

    case_a_id: UUID = Field(description="One of the two related cases (order does not matter).")
    case_b_id: UUID = Field(description="The other related case (order does not matter).")

    @model_validator(mode="after")
    def cases_must_differ(self) -> "CaseRelationshipCreate":
        if self.case_a_id == self.case_b_id:
            raise ValueError("A case cannot be related to itself.")
        return self


class CaseRelationshipRead(CaseRelationshipBase):
    """Full CaseRelationship representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_case_id: UUID = Field(
        description="Lexicographically smaller case UUID (canonical ordering).",
    )
    target_case_id: UUID = Field(
        description="Lexicographically larger case UUID (canonical ordering).",
    )
    status: RelationshipStatus = Field(
        description=(
            "potential — awaiting review | "
            "confirmed — reviewer accepted | "
            "dismissed — reviewer rejected"
        ),
    )
    confidence_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "System-computed similarity score [0.0, 1.0]. "
            "For human reference only — never triggers automatic status change."
        ),
    )
    evidence: dict | None = Field(
        default=None,
        description="Structured explanation of the signals behind this relationship.",
    )
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CaseRelationshipSummary(BaseModel):
    """Compact reference used in case detail responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_case_id: UUID
    target_case_id: UUID
    relationship_type: RelationshipType
    status: RelationshipStatus
    confidence_score: float | None = None
