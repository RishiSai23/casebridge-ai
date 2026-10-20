"""
Pydantic v2 schemas for Bureau.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BureauBase(BaseModel):
    code: str = Field(
        min_length=1,
        max_length=50,
        description="Stable uppercase code (e.g. 'PGRS', 'LEGAL').",
    )
    name: str = Field(
        min_length=1,
        max_length=300,
        description="Full human-readable bureau name.",
    )
    description: str | None = Field(
        default=None,
        description="Optional description of the bureau's mandate.",
    )
    is_active: bool = Field(default=True)

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.strip().upper()


class BureauCreate(BureauBase):
    """Payload for creating a new Bureau."""
    pass


class BureauRead(BureauBase):
    """Full Bureau representation returned by read endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class BureauSummary(BaseModel):
    """Compact reference embedded in assignment responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
