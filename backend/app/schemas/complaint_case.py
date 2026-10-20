"""
Pydantic v2 schemas for ComplaintCase.

Schema hierarchy
----------------
ComplaintCaseBase    — shared fields
ComplaintCaseCreate  — POST payload (caller sets received_at; server controls id, timestamps)
ComplaintCaseRead    — full read response including computed fields
ComplaintCaseSummary — compact representation for embedding in related objects
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models.enums import CasePriority, CaseStatus
from app.schemas.institution import InstitutionSummary


class ComplaintCaseBase(BaseModel):
    """Fields shared between create and read schemas."""

    subject: str = Field(
        min_length=1,
        max_length=500,
        description="Short subject line of the complaint.",
    )
    description: str | None = Field(
        default=None,
        description="Full complaint description.",
    )
    category: str | None = Field(
        default=None,
        max_length=100,
        description="Optional complaint category (e.g. 'fee_refund').",
    )
    priority: CasePriority = Field(
        default=CasePriority.MEDIUM,
        description="low | medium | high | critical",
    )
    received_at: datetime = Field(
        description="When the complaint was received by the platform (UTC).",
    )
    due_at: datetime | None = Field(
        default=None,
        description="Resolution deadline (UTC). Null if not yet scheduled.",
    )


class ComplaintCaseCreate(ComplaintCaseBase):
    """Payload for creating a new ComplaintCase.

    institution_id and case_reference are supplied by the caller.
    status is always initialised to 'open' by the service layer.
    """

    institution_id: UUID = Field(
        description="UUID of the Institution this complaint concerns.",
    )
    case_reference: str = Field(
        min_length=1,
        max_length=100,
        description="Human-readable unique reference (e.g. 'AICTE-PGRS-2026-001234').",
    )

    @field_validator("subject", "case_reference")
    @classmethod
    def strip_strings(cls, v: str) -> str:
        return v.strip()


class ComplaintCaseRead(ComplaintCaseBase):
    """Full ComplaintCase representation returned by read endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_reference: str
    institution_id: UUID
    institution: InstitutionSummary | None = Field(
        default=None,
        description="Embedded institution summary when eagerly loaded.",
    )
    status: CaseStatus = Field(description="open | under_review | pending_info | escalated | resolved | closed | withdrawn")
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ComplaintCaseSummary(BaseModel):
    """Compact reference used inside relationship and coordination responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_reference: str
    subject: str
    status: CaseStatus
    priority: CasePriority
