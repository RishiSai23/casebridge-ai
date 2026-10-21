"""
Unit tests for the complaint lifecycle service layer.

Covers status transition validation, closed_at management, and event
recording behaviour using plain Python objects — no database or mock session
required for the pure functions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.db.models.complaint_case import ComplaintCase
from app.db.models.enums import CaseEventType, CasePriority, CaseStatus
from app.services.case_lifecycle import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STATUSES,
    manage_closed_at,
    record_case_event,
    validate_status_transition,
)


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #

def _make_case(
    status: CaseStatus = CaseStatus.OPEN,
    closed_at: datetime | None = None,
) -> ComplaintCase:
    """Build a transient ComplaintCase (never persisted)."""
    case = ComplaintCase(
        id="00000000-0000-0000-0000-000000000001",
        case_reference="AICTE-PGRS-2026-000001",
        institution_id="00000000-0000-0000-0000-000000000002",
        subject="Test complaint",
        description=None,
        category=None,
        priority=CasePriority.MEDIUM,
        status=status,
        received_at=datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc),
        due_at=None,
        closed_at=closed_at,
    )
    return case


# --------------------------------------------------------------------------- #
# validate_status_transition                                                  #
# --------------------------------------------------------------------------- #


def test_validate_same_status_is_idempotent() -> None:
    """Re-submitting the current status is always allowed (no-op)."""
    for status in CaseStatus:
        validate_status_transition(status, status)


@pytest.mark.parametrize(
    "current,new",
    [
        (CaseStatus.OPEN, CaseStatus.UNDER_REVIEW),
        (CaseStatus.OPEN, CaseStatus.PENDING_INFO),
        (CaseStatus.OPEN, CaseStatus.ESCALATED),
        (CaseStatus.OPEN, CaseStatus.RESOLVED),
        (CaseStatus.OPEN, CaseStatus.CLOSED),
        (CaseStatus.OPEN, CaseStatus.WITHDRAWN),
        (CaseStatus.UNDER_REVIEW, CaseStatus.PENDING_INFO),
        (CaseStatus.UNDER_REVIEW, CaseStatus.ESCALATED),
        (CaseStatus.UNDER_REVIEW, CaseStatus.OPEN),
        (CaseStatus.UNDER_REVIEW, CaseStatus.RESOLVED),
        (CaseStatus.UNDER_REVIEW, CaseStatus.CLOSED),
        (CaseStatus.UNDER_REVIEW, CaseStatus.WITHDRAWN),
        (CaseStatus.PENDING_INFO, CaseStatus.UNDER_REVIEW),
        (CaseStatus.PENDING_INFO, CaseStatus.ESCALATED),
        (CaseStatus.PENDING_INFO, CaseStatus.OPEN),
        (CaseStatus.PENDING_INFO, CaseStatus.RESOLVED),
        (CaseStatus.PENDING_INFO, CaseStatus.CLOSED),
        (CaseStatus.PENDING_INFO, CaseStatus.WITHDRAWN),
        (CaseStatus.ESCALATED, CaseStatus.RESOLVED),
        (CaseStatus.ESCALATED, CaseStatus.UNDER_REVIEW),
        (CaseStatus.ESCALATED, CaseStatus.OPEN),
        (CaseStatus.ESCALATED, CaseStatus.CLOSED),
        (CaseStatus.ESCALATED, CaseStatus.WITHDRAWN),
        (CaseStatus.RESOLVED, CaseStatus.CLOSED),
        (CaseStatus.RESOLVED, CaseStatus.UNDER_REVIEW),
        (CaseStatus.RESOLVED, CaseStatus.OPEN),
        (CaseStatus.RESOLVED, CaseStatus.WITHDRAWN),
        (CaseStatus.CLOSED, CaseStatus.OPEN),
        (CaseStatus.WITHDRAWN, CaseStatus.OPEN),
    ],
)
def test_validate_allowed_transitions(current: CaseStatus, new: CaseStatus) -> None:
    """Every transition listed in ALLOWED_TRANSITIONS is accepted."""
    validate_status_transition(current, new)


@pytest.mark.parametrize(
    "current,new",
    [
        (CaseStatus.CLOSED, CaseStatus.UNDER_REVIEW),
        (CaseStatus.CLOSED, CaseStatus.PENDING_INFO),
        (CaseStatus.CLOSED, CaseStatus.ESCALATED),
        (CaseStatus.CLOSED, CaseStatus.RESOLVED),
        (CaseStatus.CLOSED, CaseStatus.WITHDRAWN),
        (CaseStatus.WITHDRAWN, CaseStatus.UNDER_REVIEW),
        (CaseStatus.WITHDRAWN, CaseStatus.PENDING_INFO),
        (CaseStatus.WITHDRAWN, CaseStatus.ESCALATED),
        (CaseStatus.WITHDRAWN, CaseStatus.RESOLVED),
        (CaseStatus.WITHDRAWN, CaseStatus.CLOSED),
    ],
)
def test_validate_invalid_transitions_from_terminal(
    current: CaseStatus, new: CaseStatus
) -> None:
    """Terminal states (except reopening to OPEN) are rejected."""
    with pytest.raises(ValueError, match="Invalid status transition"):
        validate_status_transition(current, new)


@pytest.mark.parametrize(
    "current,new",
    [
        (CaseStatus.RESOLVED, CaseStatus.PENDING_INFO),
        (CaseStatus.RESOLVED, CaseStatus.ESCALATED),
        (CaseStatus.ESCALATED, CaseStatus.PENDING_INFO),
    ],
)
def test_validate_invalid_transitions_from_non_terminal(
    current: CaseStatus, new: CaseStatus
) -> None:
    """Representative disallowed moves between non-terminal states are rejected."""
    with pytest.raises(ValueError, match="Invalid status transition"):
        validate_status_transition(current, new)


def test_validate_transition_error_message() -> None:
    """ValueError includes both status values for debugging."""
    with pytest.raises(ValueError) as exc_info:
        validate_status_transition(CaseStatus.CLOSED, CaseStatus.UNDER_REVIEW)
    assert "closed" in str(exc_info.value)
    assert "under_review" in str(exc_info.value)


# --------------------------------------------------------------------------- #
# ALLOWED_TRANSITIONS completeness                                            #
# --------------------------------------------------------------------------- #


def test_allowed_transitions_covers_all_statuses() -> None:
    """Every CaseStatus appears as a key in the transition map."""
    assert set(ALLOWED_TRANSITIONS.keys()) == set(CaseStatus)


def test_terminal_statuses_constant() -> None:
    """TERMINAL_STATUSES contains exactly CLOSED and WITHDRAWN."""
    assert TERMINAL_STATUSES == frozenset(
        {CaseStatus.CLOSED, CaseStatus.WITHDRAWN}
    )


# --------------------------------------------------------------------------- #
# manage_closed_at                                                            #
# --------------------------------------------------------------------------- #


def test_manage_closed_at_sets_on_enter_terminal() -> None:
    """Entering 'closed' from a non-terminal state sets closed_at."""
    case = _make_case(status=CaseStatus.OPEN, closed_at=None)
    manage_closed_at(case, CaseStatus.CLOSED)
    assert case.closed_at is not None
    assert case.closed_at.tzinfo is not None


def test_manage_closed_at_sets_on_enter_withdrawn() -> None:
    """Entering 'withdrawn' from a non-terminal state sets closed_at."""
    case = _make_case(status=CaseStatus.OPEN, closed_at=None)
    manage_closed_at(case, CaseStatus.WITHDRAWN)
    assert case.closed_at is not None
    assert case.closed_at.tzinfo is not None


def test_manage_closed_at_clears_on_reopen() -> None:
    """Leaving a terminal state clears closed_at."""
    stamp = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    case = _make_case(status=CaseStatus.CLOSED, closed_at=stamp)
    manage_closed_at(case, CaseStatus.OPEN)
    assert case.closed_at is None


def test_manage_closed_at_preserves_when_no_status_change() -> None:
    """When new_status is None, closed_at is untouched."""
    stamp = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    case = _make_case(status=CaseStatus.CLOSED, closed_at=stamp)
    manage_closed_at(case, None)
    assert case.closed_at == stamp


def test_manage_closed_at_preserves_same_terminal_class() -> None:
    """Transitioning between terminal statuses preserves closed_at."""
    stamp = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    case = _make_case(status=CaseStatus.CLOSED, closed_at=stamp)
    manage_closed_at(case, CaseStatus.WITHDRAWN)
    assert case.closed_at == stamp


def test_manage_closed_at_preserves_same_non_terminal_class() -> None:
    """Transitioning between non-terminal statuses preserves closed_at."""
    case = _make_case(status=CaseStatus.OPEN, closed_at=None)
    manage_closed_at(case, CaseStatus.UNDER_REVIEW)
    assert case.closed_at is None


# --------------------------------------------------------------------------- #
# record_case_event                                                           #
# --------------------------------------------------------------------------- #


def test_record_case_event_stages_on_session() -> None:
    """record_case_event adds a CaseEvent to the session without committing."""
    mock_db = MagicMock()
    case = _make_case()

    event = record_case_event(
        mock_db,
        case,
        CaseEventType.CREATED,
        "Complaint case created.",
    )

    mock_db.add.assert_called_once()
    assert event.case_id == case.id
    assert event.event_type == CaseEventType.CREATED
    assert event.description == "Complaint case created."
    assert event.actor_user_id is None
    assert event.occurred_at.tzinfo is not None


def test_record_case_event_with_metadata() -> None:
    """Event metadata is stored verbatim on the event row."""
    mock_db = MagicMock()
    case = _make_case()

    event = record_case_event(
        mock_db,
        case,
        CaseEventType.STATUS_CHANGED,
        "Status changed from 'open' to 'under_review'.",
        event_metadata={"old_status": "open", "new_status": "under_review"},
    )

    assert event.event_metadata == {
        "old_status": "open",
        "new_status": "under_review",
    }


def test_record_case_event_uses_provided_occurred_at() -> None:
    """An explicit occurred_at is respected."""
    mock_db = MagicMock()
    case = _make_case()
    explicit_ts = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)

    event = record_case_event(
        mock_db,
        case,
        CaseEventType.CREATED,
        "Complaint case created.",
        occurred_at=explicit_ts,
    )

    assert event.occurred_at == explicit_ts