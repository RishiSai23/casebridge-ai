"""
Pydantic v2 schemas for Institution.

Separation of concerns
-----------------------
SQLAlchemy models handle persistence; Pydantic schemas handle API boundaries.
ORM models are never exposed directly in responses.

Schema hierarchy
----------------
InstitutionBase      — shared fields used for both read and write
InstitutionCreate    — payload accepted by POST /institutions
InstitutionRead      — full read response (includes generated fields)
InstitutionSummary   — compact representation for embedding in related responses
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InstitutionBase(BaseModel):
    """Fields shared by create and read schemas."""

    name: str = Field(
        min_length=1,
        max_length=500,
        description="Official institution name.",
    )
    aicte_institution_id: str | None = Field(
        default=None,
        max_length=100,
        description="External AICTE identifier when known. Omit if not yet assigned.",
    )
    institution_type: str | None = Field(
        default=None,
        max_length=100,
        description="E.g. 'university', 'college', 'polytechnic'.",
    )
    state: str | None = Field(
        default=None,
        max_length=100,
        description="Indian state or union territory.",
    )
    district: str | None = Field(
        default=None,
        max_length=100,
    )


class InstitutionCreate(InstitutionBase):
    """Payload for creating a new Institution.

    normalized_name is computed server-side and must NOT be supplied by the
    caller — it will be derived from name in the service layer.
    """

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("name must not be empty after trimming whitespace")
        return stripped


class InstitutionRead(InstitutionBase):
    """Full Institution representation returned by read endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="UUID primary key.")
    normalized_name: str = Field(description="Server-computed normalised name.")
    created_at: datetime = Field(description="UTC timestamp of row creation.")
    updated_at: datetime = Field(description="UTC timestamp of last update.")


class InstitutionSummary(BaseModel):
    """Compact Institution reference for embedding inside other response objects."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    aicte_institution_id: str | None = None
    state: str | None = None


class InstitutionList(BaseModel):
    """Paginated list of institutions returned by GET /institutions."""

    items: list[InstitutionRead] = Field(
        description="Institutions on the requested page."
    )
    total: int = Field(
        ge=0,
        description="Total number of institutions matching the search criteria.",
    )
    limit: int = Field(
        ge=1,
        description="Maximum number of items on a page (page size).",
    )
    offset: int = Field(
        ge=0,
        description="Number of matching institutions skipped before this page.",
    )
