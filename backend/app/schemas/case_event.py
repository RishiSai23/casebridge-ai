"""
Pydantic v2 schemas for CaseEvent (case timeline events).

Schema hierarchy
----------------
CaseEventRead — public read representation returned by the timeline endpoint.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import CaseEventType


class CaseEventRead(BaseModel):
    """Public read representation of a case event.

    Only fields safe for API consumers are exposed.  Internal relationships
    (case, actor) are not eagerly loaded here; their IDs are included for
    client-side correlation.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Unique identifier of the event.")
    case_id: UUID = Field(
        description="UUID of the complaint case this event belongs to."
    )
    event_type: CaseEventType = Field(description="Type of event that occurred.")
    description: str = Field(description="Human-readable summary of the event.")
    actor_user_id: UUID | None = Field(
        default=None,
        description=(
            "User who triggered the event. NULL for system-generated events. "
            "No authentication layer exists yet, so all events are system-owned."
        ),
    )
    occurred_at: datetime = Field(description="When the event occurred (UTC).")
    event_metadata: dict | None = Field(
        default=None,
        description="Optional structured context for this event type.",
    )
