"""
Endpoint tests for the Complaint Case API (Module 3.2).

Endpoints under test
--------------------
POST   /api/v1/complaints          — create a complaint case (HTTP 201)
GET    /api/v1/complaints          — list complaint cases with pagination
                                       and filters (HTTP 200)
GET    /api/v1/complaints/{case_id}
                                       — retrieve one complaint case
                                       (HTTP 200 / HTTP 404)
PATCH  /api/v1/complaints/{case_id}
                                       — partially update a complaint case
                                       (HTTP 200 / HTTP 404 / HTTP 409 / HTTP 422)

Mocking strategy
----------------
Every complaint route depends on ``app.db.session.get_db``.  That dependency
is overridden with an async generator yielding a mocked
``sqlalchemy.ext.asyncio.AsyncSession``, so these tests need no PostgreSQL
instance, network access, or external service.

* ``mock_session.execute`` returns pre-configured ``unittest.mock.MagicMock``
  result objects exposing ``.scalar()``, ``.scalars().first()`` and
  ``.scalars().all()``.
* ``db.add``/``db.commit``/``db.refresh``/``db.rollback`` are configured per
  test to simulate successful persistence or a duplicate-reference conflict.

Test isolation
--------------
* ``get_settings.cache_clear()`` runs before and after every test.
* The database engine singleton is reset before and after every test.
* Dependency overrides are torn down when the test client fixture ends.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.db.session import get_db
from app.db.models.complaint_case import ComplaintCase
from app.db.models.enums import CasePriority, CaseStatus
from app.main import create_app


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture(autouse=True)
def _reset_settings_cache() -> None:
    """Clear the lru_cache on get_settings before and after each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_engine_singleton() -> None:
    """Reset the module-level engine singleton so no state leaks between tests."""
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
# Helpers
# --------------------------------------------------------------------------- #

_STAMP = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)


def _make_institution() -> object:
    """Build a transient Institution-like row (never persisted to a real DB)."""
    inst = MagicMock()
    inst.id = str(uuid4())
    inst.name = "National Institute of Technology"
    return inst


def _make_case(
    case_reference: str = "AICTE-PGRS-2026-000001",
    status: CaseStatus = CaseStatus.OPEN,
    closed_at: datetime | None = None,
    institution_id: str | None = None,
) -> ComplaintCase:
    """Build a transient ComplaintCase ORM row (never persisted to a real DB)."""
    case = ComplaintCase(
        id=str(uuid4()),
        case_reference=case_reference,
        institution_id=institution_id if institution_id is not None else str(uuid4()),
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
    # The relationship is never loaded in these mocked tests; keep it None so
    # Pydantic serialization of ComplaintCaseRead does not touch a session.
    case.institution = None
    return case


def _captured_instance(mock_session: AsyncMock) -> dict:
    """Return a dict that capture() populates with the object passed to db.add."""
    captured: dict = {}
    mock_session.add.side_effect = lambda obj: captured.setdefault("obj", obj)
    return captured


def _server_side_refresh(mock_session: AsyncMock) -> None:
    """Configure db.refresh to populate server-generated fields."""

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


# --------------------------------------------------------------------------- #
# POST /complaints
# --------------------------------------------------------------------------- #

def test_create_complaint_case_returns_201(client, mock_session):
    """Valid payload creates a case with status 'open' and returns HTTP 201."""
    captured = _captured_instance(mock_session)
    inst = _make_institution()
    inst_result = MagicMock()
    inst_result.scalars.return_value.first.return_value = inst
    mock_session.execute.return_value = inst_result
    mock_session.commit = AsyncMock()
    _server_side_refresh(mock_session)

    response = client.post("/api/v1/complaints", json=_valid_case_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["case_reference"] == "AICTE-PGRS-2026-000001"
    assert body["status"] == "open"
    assert body["closed_at"] is None
    assert body["priority"] == "high"
    assert body["id"]  # server-generated UUID
    assert body["created_at"]
    assert body["updated_at"]

    stored = captured["obj"]
    assert stored.case_reference == "AICTE-PGRS-2026-000001"
    assert stored.status == CaseStatus.OPEN
    assert stored.closed_at is None
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once()


def test_create_complaint_case_ignores_client_supplied_server_fields(
    client, mock_session
):
    """Server-controlled fields supplied by the client are safely excluded."""
    captured = _captured_instance(mock_session)
    inst = _make_institution()
    inst_result = MagicMock()
    inst_result.scalars.return_value.first.return_value = inst
    mock_session.execute.return_value = inst_result
    mock_session.commit = AsyncMock()
    _server_side_refresh(mock_session)

    payload = _valid_case_payload()
    payload["status"] = "closed"
    payload["id"] = str(uuid4())
    payload["closed_at"] = _STAMP.isoformat()
    payload["created_at"] = _STAMP.isoformat()
    payload["updated_at"] = _STAMP.isoformat()

    response = client.post("/api/v1/complaints", json=payload)

    assert response.status_code == 201
    stored = captured["obj"]
    assert stored.status == CaseStatus.OPEN
    assert stored.closed_at is None


def test_create_complaint_case_invalid_payload_returns_422(client, mock_session):
    """Invalid or incomplete payloads are rejected with HTTP 422; no write occurs."""
    captured = _captured_instance(mock_session)
    response = client.post(
        "/api/v1/complaints",
        json={"case_reference": "AICTE-PGRS-2026-000001"},
    )
    assert response.status_code == 422
    # The database layer is never reached for invalid payloads.
    mock_session.add.assert_not_called()
    assert not captured


@pytest.mark.parametrize(
    "payload",
    [
        {**_valid_case_payload(), "subject": "   "},
        {**_valid_case_payload(), "case_reference": ""},
    ],
)
def test_create_complaint_case_whitespace_values_rejected(
    client, mock_session, payload
):
    """Empty-after-trim subject or case_reference is rejected with HTTP 422."""
    captured = _captured_instance(mock_session)
    response = client.post("/api/v1/complaints", json=payload)
    assert response.status_code == 422
    mock_session.add.assert_not_called()
    assert not captured


def test_create_complaint_case_naive_received_at_rejected(client, mock_session):
    """A received_at without timezone information is rejected with HTTP 422."""
    captured = _captured_instance(mock_session)
    payload = _valid_case_payload()
    payload["received_at"] = "2026-10-20T10:00:00"
    response = client.post("/api/v1/complaints", json=payload)
    assert response.status_code == 422
    mock_session.add.assert_not_called()
    assert not captured


def test_create_complaint_case_missing_institution_returns_404(client, mock_session):
    """An unknown institution yields HTTP 404, never raw database details."""
    captured = _captured_instance(mock_session)
    empty_result = MagicMock()
    empty_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = empty_result

    response = client.post("/api/v1/complaints", json=_valid_case_payload())

    assert response.status_code == 404
    assert response.json()["detail"] == "Institution not found."
    body_text = response.text
    assert "duplicate" not in body_text.lower()
    assert "key" not in body_text.lower()
    mock_session.add.assert_not_called()
    assert not captured


def test_create_complaint_case_duplicate_reference_returns_409(client, mock_session):
    """A duplicate case_reference yields HTTP 409 after rollback, never HTTP 500."""
    inst = _make_institution()
    inst_result = MagicMock()
    inst_result.scalars.return_value.first.return_value = inst
    mock_session.execute.return_value = inst_result
    mock_session.commit = AsyncMock(
        side_effect=IntegrityError("statement", {}, Exception("duplicate key"))
    )
    mock_session.rollback = AsyncMock()

    response = client.post("/api/v1/complaints", json=_valid_case_payload())

    assert response.status_code == 409
    # Raw database errors are never leaked to the client.
    body_text = response.text
    assert "duplicate key" not in body_text
    assert "statement" not in body_text
    # db.add() is invoked before commit, so the instance was staged.
    mock_session.add.assert_called_once()
    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_awaited_once()


# --------------------------------------------------------------------------- #
# GET /complaints
# --------------------------------------------------------------------------- #

def _list_result_pair(count: int, items: list):
    count_result = MagicMock()
    count_result.scalar.return_value = count
    data_result = MagicMock()
    data_result.scalars.return_value.all.return_value = items
    return count_result, data_result


def test_list_complaint_cases_returns_paginated_page(client, mock_session):
    """A page of results returns items, total, limit and offset in order."""
    case_a = _make_case(case_reference="AICTE-PGRS-2026-000001")
    case_b = _make_case(case_reference="AICTE-PGRS-2026-000002")
    count_result, data_result = _list_result_pair(3, [case_a, case_b])
    mock_session.execute = AsyncMock(side_effect=[count_result, data_result])

    response = client.get("/api/v1/complaints?limit=2&offset=0")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"items", "total", "limit", "offset"}
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert len(body["items"]) == 2
    assert [item["case_reference"] for item in body["items"]] == [
        "AICTE-PGRS-2026-000001",
        "AICTE-PGRS-2026-000002",
    ]
    item = body["items"][0]
    assert set(item.keys()) == {
        "id",
        "case_reference",
        "institution_id",
        "subject",
        "description",
        "category",
        "priority",
        "received_at",
        "due_at",
        "status",
        "closed_at",
        "institution",
        "created_at",
        "updated_at",
    }

    # Pagination and stable ordering are pushed to the database.
    data_stmt = str(mock_session.execute.call_args_list[1][0][0])
    assert "ORDER BY" in data_stmt
    assert "LIMIT" in data_stmt
    assert "OFFSET" in data_stmt


def test_list_complaint_cases_uses_defaults(client, mock_session):
    """Omitting limit/offset applies the default page size and zero offset."""
    case = _make_case()
    count_result, data_result = _list_result_pair(1, [case])
    mock_session.execute = AsyncMock(side_effect=[count_result, data_result])

    response = client.get("/api/v1/complaints")

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert body["total"] == 1
    assert len(body["items"]) == 1


@pytest.mark.parametrize("params", [("limit", 0), ("limit", 101), ("offset", -1)])
def test_list_complaint_cases_pagination_bounds_are_enforced(
    client, mock_session, params
):
    """Out-of-bound limit/offset values are rejected with HTTP 422."""
    key, value = params
    response = client.get(f"/api/v1/complaints?{key}={value}")
    assert response.status_code == 422


def test_list_complaint_cases_filters_status_priority_institution_category(
    client, mock_session,
):
    """Status, priority, institution_id and category filters are applied."""
    inst_id = str(uuid4())
    case = _make_case(institution_id=inst_id)
    count_result, data_result = _list_result_pair(1, [case])
    mock_session.execute = AsyncMock(side_effect=[count_result, data_result])

    response = client.get(
        "/api/v1/complaints",
        params={
            "status": "open",
            "priority": "high",
            "institution_id": inst_id,
            "category": "scholarship",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1

    # The same filters are applied to the count query and the data query.
    count_stmt = str(mock_session.execute.call_args_list[0][0][0])
    data_stmt = str(mock_session.execute.call_args_list[1][0][0])
    for stmt in (count_stmt, data_stmt):
        assert "status" in stmt
        assert "priority" in stmt
        assert "institution_id" in stmt
        assert "category" in stmt


def test_list_complaint_cases_empty_result(client, mock_session):
    """A filter matching nothing returns an empty page with total 0."""
    count_result, data_result = _list_result_pair(0, [])
    mock_session.execute = AsyncMock(side_effect=[count_result, data_result])

    response = client.get("/api/v1/complaints?category=does-not-exist")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []
    assert body["limit"] == 20
    assert body["offset"] == 0


def test_list_complaint_cases_deterministic_ordering(client, mock_session):
    """Data is ordered by created_at descending with ID as tie-breaker."""
    case = _make_case()
    count_result, data_result = _list_result_pair(1, [case])
    mock_session.execute = AsyncMock(side_effect=[count_result, data_result])

    client.get("/api/v1/complaints")

    data_stmt = str(mock_session.execute.call_args_list[1][0][0])
    assert "ORDER BY" in data_stmt
    stmt_lower = data_stmt.lower()
    assert "created_at" in stmt_lower
    assert "desc" in stmt_lower
    assert "id" in stmt_lower


# --------------------------------------------------------------------------- #
# GET /complaints/{case_id}
# --------------------------------------------------------------------------- #

def test_get_complaint_case_by_id(client, mock_session):
    """Existing UUID returns the case with HTTP 200."""
    case = _make_case()
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    mock_session.execute.return_value = result

    response = client.get(f"/api/v1/complaints/{case.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == case.id
    assert body["case_reference"] == case.case_reference
    assert body["subject"] == case.subject
    assert body["status"] == case.status.value
    assert body["priority"] == case.priority.value


def test_get_complaint_case_unknown_id_returns_404(client, mock_session):
    """Unknown UUID returns HTTP 404 with a generic message."""
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = result

    response = client.get(f"/api/v1/complaints/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Complaint case not found."


def test_get_complaint_case_invalid_uuid_returns_422(client, mock_session):
    """A non-UUID path parameter is rejected with HTTP 422."""
    response = client.get("/api/v1/complaints/not-a-valid-uuid")
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# PATCH /complaints/{case_id}
# --------------------------------------------------------------------------- #

def test_patch_complaint_case_updates_only_provided_fields(client, mock_session):
    """Only explicitly provided fields are mutated; the rest stay unchanged."""
    case = _make_case()
    case.subject = "Old subject"
    case.priority = CasePriority.HIGH
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    mock_session.execute.return_value = result
    mock_session.commit = AsyncMock()
    _server_side_refresh(mock_session)

    response = client.patch(
        f"/api/v1/complaints/{case.id}",
        json={"subject": "New subject", "priority": "low"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["subject"] == "New subject"
    assert body["priority"] == "low"
    # Fields not supplied were not mutated on the ORM object.
    assert case.subject == "New subject"
    assert case.priority == CasePriority.LOW
    assert case.description == "Student reports repeated payment delays."
    assert case.status == CaseStatus.OPEN
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once()


def test_patch_complaint_case_null_due_at_clears(client, mock_session):
    """An explicit null due_at clears the value."""
    case = _make_case()
    case.due_at = _STAMP
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    mock_session.execute.return_value = result
    mock_session.commit = AsyncMock()
    _server_side_refresh(mock_session)

    response = client.patch(
        f"/api/v1/complaints/{case.id}", json={"due_at": None}
    )

    assert response.status_code == 200
    assert response.json()["due_at"] is None
    assert case.due_at is None


def test_patch_complaint_case_omitted_due_at_preserved(client, mock_session):
    """An omitted due_at leaves the existing value untouched."""
    case = _make_case()
    case.due_at = _STAMP
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    mock_session.execute.return_value = result
    mock_session.commit = AsyncMock()
    _server_side_refresh(mock_session)

    response = client.patch(f"/api/v1/complaints/{case.id}", json={"subject": "x"})

    assert response.status_code == 200
    assert case.due_at == _STAMP


def test_patch_complaint_case_empty_payload_rejected(client, mock_session):
    """An empty PATCH body is rejected with HTTP 422."""
    case = _make_case()
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    mock_session.execute.return_value = result

    response = client.patch(f"/api/v1/complaints/{case.id}", json={})

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"subject": "   "},
        {"subject": ""},
        {"status": "bogus"},
        {"priority": "bogus"},
        {"due_at": "2026-10-20T10:00:00"},
        {"subject": "x" * 501},
    ],
)
def test_patch_complaint_case_invalid_values_rejected(client, mock_session, payload):
    """Invalid subject, enum, naive due_at or oversized subject yield HTTP 422."""
    case = _make_case()
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    mock_session.execute.return_value = result

    response = client.patch(f"/api/v1/complaints/{case.id}", json=payload)

    assert response.status_code == 422


def test_patch_complaint_case_protected_fields_rejected(client, mock_session):
    """Attempting to change protected fields is rejected with HTTP 422."""
    case = _make_case()
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    mock_session.execute.return_value = result

    response = client.patch(
        f"/api/v1/complaints/{case.id}",
        json={
            "id": str(uuid4()),
            "case_reference": "AICTE-PGRS-999999",
            "institution_id": str(uuid4()),
            "received_at": _STAMP.isoformat(),
        },
    )

    assert response.status_code == 422


def test_patch_complaint_case_missing_case_returns_404(client, mock_session):
    """Unknown UUID returns HTTP 404 with a generic message."""
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = result

    response = client.patch(f"/api/v1/complaints/{uuid4()}", json={"subject": "x"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Complaint case not found."


def test_patch_complaint_case_integrity_conflict_returns_409(client, mock_session):
    """An integrity conflict on update yields HTTP 409 after rollback."""
    case = _make_case()
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    mock_session.execute.return_value = result
    mock_session.commit = AsyncMock(
        side_effect=IntegrityError("statement", {}, Exception("duplicate key"))
    )
    mock_session.rollback = AsyncMock()

    response = client.patch(
        f"/api/v1/complaints/{case.id}", json={"subject": "x"}
    )

    assert response.status_code == 409
    body_text = response.text
    assert "duplicate key" not in body_text
    assert "statement" not in body_text
    mock_session.rollback.assert_awaited_once()


def test_patch_complaint_case_closing_sets_closed_at(client, mock_session):
    """Transitioning to 'closed' sets closed_at to the current UTC time."""
    case = _make_case(status=CaseStatus.OPEN, closed_at=None)
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    mock_session.execute.return_value = result
    mock_session.commit = AsyncMock()
    _server_side_refresh(mock_session)

    response = client.patch(
        f"/api/v1/complaints/{case.id}", json={"status": "closed"}
    )

    assert response.status_code == 200
    assert case.closed_at is not None
    assert case.closed_at.tzinfo is not None
    assert response.json()["closed_at"] is not None


def test_patch_complaint_case_withdrawing_sets_closed_at(client, mock_session):
    """Transitioning to 'withdrawn' sets closed_at to the current UTC time."""
    case = _make_case(status=CaseStatus.OPEN, closed_at=None)
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    mock_session.execute.return_value = result
    mock_session.commit = AsyncMock()
    _server_side_refresh(mock_session)

    response = client.patch(
        f"/api/v1/complaints/{case.id}", json={"status": "withdrawn"}
    )

    assert response.status_code == 200
    assert case.closed_at is not None
    assert case.closed_at.tzinfo is not None


def test_patch_complaint_case_reopening_clears_closed_at(client, mock_session):
    """Moving from a terminal status to a non-terminal one clears closed_at."""
    case = _make_case(status=CaseStatus.CLOSED, closed_at=_STAMP)
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    mock_session.execute.return_value = result
    mock_session.commit = AsyncMock()
    _server_side_refresh(mock_session)

    response = client.patch(
        f"/api/v1/complaints/{case.id}", json={"status": "open"}
    )

    assert response.status_code == 200
    assert case.closed_at is None


def test_patch_complaint_case_other_update_preserves_closed_at(
    client, mock_session,
):
    """Non-status updates preserve the existing closed_at."""
    case = _make_case(status=CaseStatus.CLOSED, closed_at=_STAMP)
    result = MagicMock()
    result.scalars.return_value.first.return_value = case
    mock_session.execute.return_value = result
    mock_session.commit = AsyncMock()
    _server_side_refresh(mock_session)

    response = client.patch(
        f"/api/v1/complaints/{case.id}", json={"subject": "Updated subject"}
    )

    assert response.status_code == 200
    assert case.closed_at == _STAMP
    assert case.status == CaseStatus.CLOSED