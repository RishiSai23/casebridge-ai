"""
Endpoint and integration tests for case event recording and the timeline API.

Covers:
* CREATED event recorded on complaint case creation (POST /complaints)
* STATUS_CHANGED event recorded on status transition (PATCH /complaints/{id})
* PRIORITY_CHANGED event recorded on priority change
* No duplicate STATUS_CHANGED event for idempotent status updates
* Transactional rollback: failed commit rolls back case + events together
* Timeline endpoint: chronological ordering, stable tie-breaker, empty collection,
  404 for unknown case, 422 for invalid UUID, no cross-case leakage

Mocking strategy
----------------
Every complaint route depends on ``app.db.session.get_db``.  That dependency
is overridden with an async generator yielding a mocked
``sqlalchemy.ext.asyncio.AsyncSession``, so these tests need no PostgreSQL
instance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.db.session import get_db
from app.db.models.case_event import CaseEvent
from app.db.models.complaint_case import ComplaintCase
from app.db.models.enums import CaseEventType, CasePriority, CaseStatus
from app.main import create_app


# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #

@pytest.fixture(autouse=True)
def _reset_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_engine_singleton() -> None:
    from app.db import session as session_module

    session_module._engine = None
    session_module._session_factory = None
    yield
    session_module._engine = None
    session_module._session_factory = None


@pytest.fixture
def mock_session() -> AsyncMock:
    """A mocked AsyncSession with the methods the complaint routes use."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def client(mock_session: AsyncMock) -> TestClient:
    """A TestClient whose get_db dependency yields mock_session."""

    async def _override_get_db():
        yield mock_session

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #

_STAMP = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)


def _make_institution() -> MagicMock:
    inst = MagicMock()
    inst.id = str(uuid4())
    inst.name = "National Institute of Technology"
    return inst


def _make_case(
    case_reference: str = "AICTE-PGRS-2026-000001",
    status: CaseStatus = CaseStatus.OPEN,
    closed_at: datetime | None = None,
) -> ComplaintCase:
    case = ComplaintCase(
        id=str(uuid4()),
        case_reference=case_reference,
        institution_id=str(uuid4()),
        subject="Delayed scholarship disbursement",
        description="Student reports repeated payment delays.",
        category="scholarship",
        priority=CasePriority.HIGH,
        status=status,
        received_at=_STAMP,
        due_at=_STAMP,
        closed_at=closed_at,
        created_at=_STAMP,
        updated_at=_STAMP,
    )
    case.institution = None
    return case


def _captured_instance(mock_session: AsyncMock) -> dict:
    """Attach a side_effect that records every object passed to db.add."""
    captured: dict = {}
    mock_session.add.side_effect = lambda obj: captured.setdefault("objs", []).append(obj)
    return captured


def _captured_events(mock_session: AsyncMock) -> list:
    """Return all CaseEvent instances passed to db.add, in order added."""
    events: list[CaseEvent] = []
    for call in mock_session.add.call_args_list:
        if not call.args:
            continue
        obj = call.args[0]
        if isinstance(obj, CaseEvent):
            events.append(obj)
    return events


def _select_bindparam_values(statement) -> set[str]:
    """Return string-normalized bind values from a compiled SELECT."""
    compiled = statement.compile(dialect=postgresql.dialect())
    return {str(value) for value in compiled.params.values()}


def _server_side_refresh(mock_session: AsyncMock) -> None:
    async def _refresh(obj) -> None:
        obj.id = str(uuid4())
        obj.created_at = datetime(2026, 10, 20, 10, 30, 0, tzinfo=timezone.utc)
        obj.updated_at = datetime(2026, 10, 20, 10, 30, 0, tzinfo=timezone.utc)

    mock_session.refresh.side_effect = _refresh


def _valid_case_payload() -> dict:
    return {
        "institution_id": str(uuid4()),
        "case_reference": "AICTE-PGRS-2026-000001",
        "subject": "Delayed scholarship disbursement",
        "description": "Student reports repeated payment delays.",
        "category": "scholarship",
        "priority": "high",
        "received_at": _STAMP.isoformat(),
        "due_at": _STAMP.replace(day=27).isoformat(),
    }


def _setup_institution_mock(mock_session: AsyncMock) -> MagicMock:
    inst = _make_institution()
    inst_result = MagicMock()
    inst_result.scalars.return_value.first.return_value = inst
    mock_session.execute.return_value = inst_result
    return inst


# --------------------------------------------------------------------------- #
# POST /complaints — creation event                                           #
# --------------------------------------------------------------------------- #

def test_create_complaint_case_records_created_event(client, mock_session):
    """POST creates the case and a CREATED event in the same transaction."""
    captured = _captured_instance(mock_session)
    _setup_institution_mock(mock_session)
    mock_session.commit = AsyncMock()
    _server_side_refresh(mock_session)

    response = client.post("/api/v1/complaints", json=_valid_case_payload())

    assert response.status_code == 201
    events = _captured_events(mock_session)
    assert len(events) == 1
    assert events[0].event_type == CaseEventType.CREATED
    assert events[0].description == "Complaint case created."
    assert events[0].actor_user_id is None


def test_create_complaint_case_duplicate_reference_rolls_back_event(
    client, mock_session,
):
    """A duplicate reference rolls back both the case and its CREATED event."""
    inst = _make_institution()
    inst_result = MagicMock()
    inst_result.scalars.return_value.first.return_value = inst
    mock_session.execute.return_value = inst_result
    mock_session.commit = AsyncMock(
        side_effect=IntegrityError("statement", {}, Exception("duplicate key"))
    )
    mock_session.rollback = AsyncMock()

    captured = _captured_instance(mock_session)

    response = client.post("/api/v1/complaints", json=_valid_case_payload())

    assert response.status_code == 409
    mock_session.rollback.assert_awaited_once()
    # Both the case and the event were added before commit; both are rolled back.
    events = _captured_events(mock_session)
    assert len(events) == 1
    assert events[0].event_type == CaseEventType.CREATED


# --------------------------------------------------------------------------- #
# PATCH /complaints/{case_id} — status-change event                           #
# --------------------------------------------------------------------------- #

def test_patch_status_change_records_event(client, mock_session):
    """PATCH status change records a STATUS_CHANGED event with old/new values."""
    case = _make_case(status=CaseStatus.OPEN, closed_at=None)
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    mock_session.execute.return_value = result
    mock_session.commit = AsyncMock()
    _server_side_refresh(mock_session)

    response = client.patch(
        f"/api/v1/complaints/{case.id}", json={"status": "under_review"}
    )

    assert response.status_code == 200
    events = _captured_events(mock_session)
    status_events = [e for e in events if e.event_type == CaseEventType.STATUS_CHANGED]
    assert len(status_events) == 1
    assert status_events[0].event_metadata == {
        "old_status": "open",
        "new_status": "under_review",
    }
    assert "Status changed from 'open' to 'under_review'." in status_events[0].description


def test_patch_idempotent_status_no_duplicate_event(client, mock_session):
    """Re-submitting the current status creates no STATUS_CHANGED event."""
    case = _make_case(status=CaseStatus.OPEN, closed_at=None)
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    mock_session.execute.return_value = result
    mock_session.commit = AsyncMock()
    _server_side_refresh(mock_session)

    response = client.patch(
        f"/api/v1/complaints/{case.id}", json={"status": "open"}
    )

    assert response.status_code == 200
    events = _captured_events(mock_session)
    status_events = [e for e in events if e.event_type == CaseEventType.STATUS_CHANGED]
    assert len(status_events) == 0


def test_patch_integrity_conflict_rolls_back_staged_events(client, mock_session):
    """A failed commit rolls back both the case mutation and staged events."""
    case = _make_case(status=CaseStatus.OPEN, closed_at=None)
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    mock_session.execute.return_value = result
    mock_session.commit = AsyncMock(
        side_effect=IntegrityError("statement", {}, Exception("duplicate key"))
    )
    mock_session.rollback = AsyncMock()

    response = client.patch(
        f"/api/v1/complaints/{case.id}", json={"status": "under_review"}
    )

    assert response.status_code == 409
    mock_session.rollback.assert_awaited_once()
    assert len(_captured_events(mock_session)) == 1


def test_patch_invalid_transition_returns_422(client, mock_session):
    """An invalid status transition (e.g. CLOSED -> UNDER_REVIEW) returns 422."""
    case = _make_case(status=CaseStatus.CLOSED, closed_at=_STAMP)
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    mock_session.execute.return_value = result

    response = client.patch(
        f"/api/v1/complaints/{case.id}", json={"status": "under_review"}
    )

    assert response.status_code == 422
    # No events should have been staged before the validation failure.
    assert len(_captured_events(mock_session)) == 0
    mock_session.commit.assert_not_awaited()


def test_patch_idempotent_priority_no_duplicate_event(client, mock_session):
    """Re-submitting the current priority creates no PRIORITY_CHANGED event."""
    case = _make_case(status=CaseStatus.OPEN)
    case.priority = CasePriority.HIGH
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    mock_session.execute.return_value = result
    mock_session.commit = AsyncMock()
    _server_side_refresh(mock_session)

    response = client.patch(
        f"/api/v1/complaints/{case.id}", json={"priority": "high"}
    )

    assert response.status_code == 200
    priority_events = [
        e for e in _captured_events(mock_session)
        if e.event_type == CaseEventType.PRIORITY_CHANGED
    ]
    assert len(priority_events) == 0


def test_patch_priority_change_records_event(client, mock_session):
    """PATCH priority change records a PRIORITY_CHANGED event."""
    case = _make_case(status=CaseStatus.OPEN)
    case.priority = CasePriority.MEDIUM
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    mock_session.execute.return_value = result
    mock_session.commit = AsyncMock()
    _server_side_refresh(mock_session)

    response = client.patch(
        f"/api/v1/complaints/{case.id}", json={"priority": "critical"}
    )

    assert response.status_code == 200
    events = _captured_events(mock_session)
    priority_events = [e for e in events if e.event_type == CaseEventType.PRIORITY_CHANGED]
    assert len(priority_events) == 1
    assert priority_events[0].event_metadata == {
        "old_priority": "medium",
        "new_priority": "critical",
    }


# --------------------------------------------------------------------------- #
# GET /complaints/{case_id}/events — timeline endpoint                        #
# --------------------------------------------------------------------------- #

def _events_result(events: list[CaseEvent]) -> MagicMock:
    """Build a mocked execute result that returns the given events."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = events
    return result


def _case_exists_result(case: ComplaintCase | None) -> MagicMock:
    """Build a mocked execute result for the case-existence check."""
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    return result


def _make_event(
    case_id: str,
    event_type: CaseEventType,
    occurred_at: datetime,
    description: str = "Test event.",
    event_id: str | None = None,
) -> CaseEvent:
    return CaseEvent(
        id=event_id or str(uuid4()),
        case_id=case_id,
        event_type=event_type,
        description=description,
        actor_user_id=None,
        occurred_at=occurred_at,
        event_metadata=None,
    )


def test_timeline_returns_events_chronologically(client, mock_session):
    """GET /{case_id}/events returns events ordered by occurred_at ascending."""
    case = _make_case()
    case_id = case.id

    t1 = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 10, 20, 11, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)

    # Mock returns rows in DB sort order (occurred_at asc, id asc).
    events = [
        _make_event(case_id, CaseEventType.STATUS_CHANGED, t1, "First event"),
        _make_event(case_id, CaseEventType.PRIORITY_CHANGED, t2, "Second event"),
        _make_event(case_id, CaseEventType.CREATED, t3, "Third event"),
    ]

    # First execute call: case existence check; second: events query
    mock_session.execute = AsyncMock(side_effect=[_case_exists_result(case), _events_result(events)])

    response = client.get(f"/api/v1/complaints/{case_id}/events")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    assert body[0]["description"] == "First event"
    assert body[1]["description"] == "Second event"
    assert body[2]["description"] == "Third event"
    assert body[0]["event_type"] == "status_changed"
    assert body[1]["event_type"] == "priority_changed"
    assert body[2]["event_type"] == "created"


def test_timeline_stable_ordering_for_equal_timestamps(client, mock_session):
    """Equal occurred_at values are ordered deterministically by id."""
    case = _make_case()
    case_id = case.id

    same_ts = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    id_a = "00000000-0000-0000-0000-000000000001"
    id_b = "00000000-0000-0000-0000-000000000002"

    events = [
        _make_event(case_id, CaseEventType.STATUS_CHANGED, same_ts, "Event A", event_id=id_a),
        _make_event(case_id, CaseEventType.CREATED, same_ts, "Event B", event_id=id_b),
    ]

    mock_session.execute = AsyncMock(side_effect=[_case_exists_result(case), _events_result(events)])

    response = client.get(f"/api/v1/complaints/{case_id}/events")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["id"] == id_a
    assert body[0]["description"] == "Event A"
    assert body[1]["id"] == id_b
    assert body[1]["description"] == "Event B"


def test_timeline_empty_collection(client, mock_session):
    """A case with no events returns an empty list."""
    case = _make_case()
    case_id = case.id

    mock_session.execute = AsyncMock(
        side_effect=[_case_exists_result(case), _events_result([])]
    )

    response = client.get(f"/api/v1/complaints/{case_id}/events")

    assert response.status_code == 200
    assert response.json() == []


def test_timeline_unknown_case_returns_404(client, mock_session):
    """GET /{case_id}/events for a non-existent case returns HTTP 404."""
    mock_session.execute = AsyncMock(return_value=_case_exists_result(None))

    response = client.get(f"/api/v1/complaints/{uuid4()}/events")

    assert response.status_code == 404
    assert response.json()["detail"] == "Complaint case not found."


def test_timeline_invalid_uuid_returns_422(client, mock_session):
    """A non-UUID path parameter returns HTTP 422."""
    response = client.get("/api/v1/complaints/not-a-valid-uuid/events")
    assert response.status_code == 422


def test_case_timeline_endpoint_is_read_only(client):
    """The timeline route exposes GET only — events are append-only via the API."""
    app = create_app()
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.endswith("/complaints/{case_id}/events"):
            assert route.methods - {"HEAD"} == {"GET"}


def test_timeline_no_cross_case_leakage(client, mock_session):
    """Events from one case are never returned for another case."""
    case_a = _make_case(case_reference="AICTE-PGRS-2026-000001")
    case_b = _make_case(case_reference="AICTE-PGRS-2026-000002")

    t1 = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    events_b = [
        _make_event(case_b.id, CaseEventType.CREATED, t1, "Case B event"),
    ]

    # Case existence for case_a, then case_a's events (empty)
    mock_session.execute = AsyncMock(
        side_effect=[_case_exists_result(case_a), _events_result([])]
    )

    response = client.get(f"/api/v1/complaints/{case_a.id}/events")

    assert response.status_code == 200
    assert response.json() == []

    # Verify the events query bind parameters scope to case_a, not case_b.
    events_stmt = mock_session.execute.call_args_list[1][0][0]
    bind_values = _select_bindparam_values(events_stmt)
    assert str(case_a.id) in bind_values
    assert str(case_b.id) not in bind_values
    # Mock returns no rows for case_a; case_b events must not appear in the response.
    assert events_b[0].case_id == case_b.id