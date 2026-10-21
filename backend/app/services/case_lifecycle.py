"""
Complaint lifecycle service — status transition validation and event recording.

This module centralises all business rules for complaint case lifecycle
management:

* Permitted status transitions between ``CaseStatus`` values.
* ``closed_at`` management when entering or leaving terminal states.
* Append-only case event recording (``CaseEvent``) that shares the caller's
  database session/transaction so complaint mutations and event writes are
  atomic.

All functions are intentionally side-effect limited: validation functions are
pure, ``manage_closed_at`` mutates the ORM object in place, and
``record_case_event`` only stages an event on the session — the caller owns
the commit boundary.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case_event import CaseEvent
from app.db.models.complaint_case import ComplaintCase
from app.db.models.enums import CaseEventType, CaseStatus


# --------------------------------------------------------------------------- #
# Terminal statuses                                                           #
# --------------------------------------------------------------------------- #

TERMINAL_STATUSES: frozenset[CaseStatus] = frozenset(
    {CaseStatus.CLOSED, CaseStatus.WITHDRAWN}
)

# --------------------------------------------------------------------------- #
# Permitted status transitions                                                #
# --------------------------------------------------------------------------- #
#
# The transition map below defines which status a case may move *from* (key)
# to which statuses (value set).  Same-status transitions are always allowed
# (idempotent) and are deliberately omitted.
#
# Design notes:
#   * OPEN can progress down any path or jump straight to a terminal state.
#   * UNDER_REVIEW, PENDING_INFO, ESCALATED and RESOLVED are intermediate
#     states that may progress, regress to OPEN, or move to a terminal state.
#   * CLOSED and WITHDRAWN are terminal: the only permitted exit is back to
#     OPEN (reopening a case).
#   * WITHDRAWN is reachable from any non-terminal state ("at any open stage"
#     per the enum docstring in app/db/models/enums.py).
ALLOWED_TRANSITIONS: dict[CaseStatus, frozenset[CaseStatus]] = {
    CaseStatus.OPEN: frozenset(
        {
            CaseStatus.UNDER_REVIEW,
            CaseStatus.PENDING_INFO,
            CaseStatus.ESCALATED,
            CaseStatus.RESOLVED,
            CaseStatus.CLOSED,
            CaseStatus.WITHDRAWN,
        }
    ),
    CaseStatus.UNDER_REVIEW: frozenset(
        {
            CaseStatus.PENDING_INFO,
            CaseStatus.ESCALATED,
            CaseStatus.OPEN,
            CaseStatus.RESOLVED,
            CaseStatus.CLOSED,
            CaseStatus.WITHDRAWN,
        }
    ),
    CaseStatus.PENDING_INFO: frozenset(
        {
            CaseStatus.UNDER_REVIEW,
            CaseStatus.ESCALATED,
            CaseStatus.OPEN,
            CaseStatus.RESOLVED,
            CaseStatus.CLOSED,
            CaseStatus.WITHDRAWN,
        }
    ),
    CaseStatus.ESCALATED: frozenset(
        {
            CaseStatus.RESOLVED,
            CaseStatus.UNDER_REVIEW,
            CaseStatus.OPEN,
            CaseStatus.CLOSED,
            CaseStatus.WITHDRAWN,
        }
    ),
    CaseStatus.RESOLVED: frozenset(
        {
            CaseStatus.CLOSED,
            CaseStatus.UNDER_REVIEW,
            CaseStatus.OPEN,
            CaseStatus.WITHDRAWN,
        }
    ),
    CaseStatus.CLOSED: frozenset({CaseStatus.OPEN}),
    CaseStatus.WITHDRAWN: frozenset({CaseStatus.OPEN}),
}


# --------------------------------------------------------------------------- #
# Status transition validation                                                #
# --------------------------------------------------------------------------- #


def validate_status_transition(
    current_status: CaseStatus,
    new_status: CaseStatus,
) -> None:
    """Validate that a status transition is permitted.

    Parameters
    ----------
    current_status : CaseStatus
        The case's current status.
    new_status : CaseStatus
        The requested new status.

    Raises
    ------
    ValueError
        If the transition is not in the allowed transition map.
        Same-status transitions are always permitted (idempotent).
    """
    if current_status == new_status:
        return  # idempotent — re-submitting the same status is a no-op

    allowed = ALLOWED_TRANSITIONS.get(current_status, frozenset())
    if new_status not in allowed:
        raise ValueError(
            f"Invalid status transition from '{current_status.value}' "
            f"to '{new_status.value}'."
        )


# --------------------------------------------------------------------------- #
# closed_at management                                                        #
# --------------------------------------------------------------------------- #


def manage_closed_at(
    case: ComplaintCase,
    new_status: CaseStatus | None,
) -> None:
    """Update ``closed_at`` on the case based on terminal-status transitions.

    Sets ``closed_at`` to the current UTC time when entering a terminal state
    (``closed`` / ``withdrawn``) from a non-terminal one, and clears it when
    leaving a terminal state.  Preserves the existing value otherwise.

    Parameters
    ----------
    case : ComplaintCase
        The case being updated — mutated in place.
    new_status : CaseStatus | None
        The new status, or ``None`` if status is not being changed.
    """
    if new_status is None:
        return

    was_terminal = case.status in TERMINAL_STATUSES
    is_terminal = new_status in TERMINAL_STATUSES

    if is_terminal and not was_terminal:
        case.closed_at = datetime.now(timezone.utc)
    elif not is_terminal and was_terminal:
        case.closed_at = None
    # Otherwise: same terminal/non-terminal class — preserve existing closed_at.


# --------------------------------------------------------------------------- #
# Event recording                                                             #
# --------------------------------------------------------------------------- #


def record_case_event(
    db: AsyncSession,
    case: ComplaintCase,
    event_type: CaseEventType,
    description: str,
    event_metadata: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> CaseEvent:
    """Append a case event to the current session/transaction.

    The event is added to the session but not committed — the caller controls
    the commit boundary so the complaint mutation and event write are atomic.
    If the transaction is rolled back, the event is rolled back too.

    Parameters
    ----------
    db : AsyncSession
        The active async database session shared with the complaint mutation.
    case : ComplaintCase
        The case the event belongs to.
    event_type : CaseEventType
        Type of event being recorded.
    description : str
        Human-readable summary of what happened.
    event_metadata : dict | None
        Optional structured context (old/new values, etc.).  Must not contain
        credentials, passwords, or sensitive PII.
    occurred_at : datetime | None
        When the event occurred (UTC).  Defaults to the current UTC time.

    Returns
    -------
    CaseEvent
        The newly created event instance, staged on the session.
    """
    event = CaseEvent(
        case_id=case.id,
        event_type=event_type,
        description=description,
        actor_user_id=None,  # system-generated; no authentication layer yet
        occurred_at=occurred_at or datetime.now(timezone.utc),
        event_metadata=event_metadata,
    )
    db.add(event)
    return event
