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

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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

    @field_validator("received_at", "due_at")
    @classmethod
    def require_timezone_aware_datetime(cls, v: datetime | None, info: object) -> datetime | None:
        if v is None:
            return None
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            field_name = getattr(info, "field_name", "datetime")
            raise ValueError(f"{field_name} must include timezone information")
        return v


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

    @field_validator("subject", "case_reference", mode="before")
    @classmethod
    def strip_strings(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("value must not be empty after trimming whitespace")
        return stripped


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


class ComplaintCaseUpdate(BaseModel):
    """Payload for PATCH /api/v1/complaints/{case_id}.

    Every field is optional so callers update only the fields that changed.
    Omitted fields are distinguished from explicitly provided nulls via
    ``model_dump(exclude_unset=True)`` — this matters for nullable fields
    such as ``due_at``, where an explicit ``null`` means "clear the value".
    Unexpected fields (including server-controlled ones) are rejected with
    HTTP 422 by the strict schema.
    """

    model_config = ConfigDict(extra="forbid")

    subject: str | None = Field(
        default=None,
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
    priority: CasePriority | None = Field(
        default=None,
        description="low | medium | high | critical",
    )
    status: CaseStatus | None = Field(
        default=None,
        description="open | under_review | pending_info | escalated | resolved | closed | withdrawn",
    )
    due_at: datetime | None = Field(
        default=None,
        description="Resolution deadline (UTC). Explicit null clears the value.",
    )

    @field_validator("subject", mode="before")
    @classmethod
    def strip_subject(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            raise ValueError("subject must not be empty after trimming whitespace")
        return stripped

    @field_validator("due_at")
    @classmethod
    def require_timezone_aware_due_at(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return None
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("due_at must include timezone information")
        return v

    @model_validator(mode="after")
    def reject_empty_payload(self) -> "ComplaintCaseUpdate":
        if not self.model_fields_set:
            raise ValueError("PATCH payload must include at least one field to update")
        return self


class ComplaintCaseList(BaseModel):
    """Paginated list of complaint cases returned by GET /complaints."""

    items: list[ComplaintCaseRead] = Field(
        description="Complaint cases on the requested page."
    )
    total: int = Field(
        ge=0,
        description="Total number of complaint cases matching the filters.",
    )
    limit: int = Field(
        ge=1,
        description="Maximum number of items on a page (page size).",
    )
    offset: int = Field(
        ge=0,
        description="Number of matching complaint cases skipped before this page.",
    )
