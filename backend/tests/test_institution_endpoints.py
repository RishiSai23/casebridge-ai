"""
Endpoint tests for the Institution API (Module 3.1).

Endpoints under test
--------------------
POST   /api/v1/institutions          — create an institution (HTTP 201)
GET    /api/v1/institutions          — list institutions with pagination
                                          and search (HTTP 200)
GET    /api/v1/institutions/{institution_id}
                                          — retrieve one institution
                                          (HTTP 200 / HTTP 404)

Mocking strategy
----------------
Every institution route depends on ``app.db.session.get_db``.  That dependency
is overridden with an async generator yielding a mocked
``sqlalchemy.ext.asyncio.AsyncSession``, so these tests need no PostgreSQL
instance, network access, or external service.

* ``mock_session.execute`` returns pre-configured ``unittest.mock.MagicMock``
  result objects exposing ``.scalar()``, ``.scalars().first()`` and
  ``.scalars().all()``.
* ``db.add``/``db.commit``/``db.refresh``/``db.rollback`` are configured per
  test to simulate successful persistence or a duplicate-identifier conflict.

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
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.db.session import get_db
from app.db.models.institution import Institution
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
    """A mocked AsyncSession with the methods the institution routes use."""
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

def _make_institution(
    name: str = "National Institute of Technology",
    aicte_institution_id: str | None = "AICTE-1234",
    institution_type: str = "college",
    state: str = "Karnataka",
    district: str = "Bengaluru Urban",
) -> Institution:
    """Build a transient Institution ORM row (never persisted to a real DB)."""
    stamp = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    return Institution(
        id=str(uuid4()),
        name=name,
        normalized_name=" ".join(name.split()).lower(),
        aicte_institution_id=aicte_institution_id,
        institution_type=institution_type,
        state=state,
        district=district,
        created_at=stamp,
        updated_at=stamp,
    )


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


# --------------------------------------------------------------------------- #
# POST /institutions
# --------------------------------------------------------------------------- #

def test_create_institution_returns_201(client, mock_session):
    """Valid payload creates an institution and returns HTTP 201."""
    captured = _captured_instance(mock_session)
    mock_session.commit = AsyncMock()
    _server_side_refresh(mock_session)

    response = client.post(
        "/api/v1/institutions",
        json={
            "name": "  National Institute of Technology  ",
            "aicte_institution_id": "AICTE-1234",
            "institution_type": "college",
            "state": "Karnataka",
            "district": "Bengaluru Urban",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "National Institute of Technology"
    assert body["normalized_name"] == "national institute of technology"
    assert body["aicte_institution_id"] == "AICTE-1234"
    assert body["institution_type"] == "college"
    assert body["state"] == "Karnataka"
    assert body["district"] == "Bengaluru Urban"
    assert body["id"]  # server-generated UUID
    assert body["created_at"]
    assert body["updated_at"]

    stored = captured["obj"]
    assert stored.name == "National Institute of Technology"
    assert stored.normalized_name == "national institute of technology"
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once()


def test_create_institution_ignores_client_supplied_normalized_name(
    client, mock_session
):
    """normalized_name is computed server-side; a caller-supplied value is ignored."""
    captured = _captured_instance(mock_session)
    mock_session.commit = AsyncMock()
    _server_side_refresh(mock_session)

    response = client.post(
        "/api/v1/institutions",
        json={"name": "Demo College", "normalized_name": "malicious-client-value"},
    )

    assert response.status_code == 201
    assert response.json()["normalized_name"] == "demo college"
    assert captured["obj"].normalized_name == "demo college"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": ""},
        {"name": "   "},
        {"name": "Valid College", "aicte_institution_id": "x" * 101},
        {"name": "Valid College", "institution_type": "x" * 101},
    ],
)
def test_create_institution_invalid_payload_returns_422(
    client, mock_session, payload
):
    """Invalid or incomplete payloads are rejected with HTTP 422."""
    response = client.post("/api/v1/institutions", json=payload)
    assert response.status_code == 422
    # The database layer is never reached for invalid payloads.
    mock_session.add.assert_not_called()


def test_create_institution_duplicate_aicte_id_returns_409(client, mock_session):
    """A duplicate non-null AICTE ID yields HTTP 409, never HTTP 500."""
    mock_session.commit = AsyncMock(
        side_effect=IntegrityError("statement", {}, Exception("duplicate key"))
    )
    mock_session.rollback = AsyncMock()

    response = client.post(
        "/api/v1/institutions",
        json={"name": "Duplicate College", "aicte_institution_id": "AICTE-DUP"},
    )

    assert response.status_code == 409
    # Raw database errors are never leaked to the client.
    body_text = response.text
    assert "duplicate key" not in body_text
    assert "statement" not in body_text
    mock_session.rollback.assert_awaited_once()


# --------------------------------------------------------------------------- #
# GET /institutions
# --------------------------------------------------------------------------- #

def test_list_institutions_returns_paginated_page(client, mock_session):
    """Page 1 of a 3-institution result set returns 2 items with stable order."""
    inst_alpha = _make_institution(name="Alpha College", aicte_institution_id="AICTE-AAA")
    inst_beta = _make_institution(name="Beta College", aicte_institution_id="AICTE-BBB")

    count_result = MagicMock()
    count_result.scalar.return_value = 3
    data_result = MagicMock()
    data_result.scalars.return_value.all.return_value = [inst_alpha, inst_beta]
    mock_session.execute = AsyncMock(side_effect=[count_result, data_result])

    response = client.get("/api/v1/institutions?limit=2&offset=0")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"items", "total", "limit", "offset"}
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert len(body["items"]) == 2
    assert [item["name"] for item in body["items"]] == ["Alpha College", "Beta College"]
    item = body["items"][0]
    assert set(item.keys()) == {
        "id",
        "name",
        "aicte_institution_id",
        "institution_type",
        "state",
        "district",
        "normalized_name",
        "created_at",
        "updated_at",
    }

    # Pagination and stable ordering are pushed to the database, not done in Python.
    data_stmt = str(mock_session.execute.call_args_list[1][0][0])
    assert "ORDER BY" in data_stmt
    assert "LIMIT" in data_stmt
    assert "OFFSET" in data_stmt


def test_list_institutions_uses_defaults(client, mock_session):
    """Omitting limit/offset applies the default page size and zero offset."""
    inst = _make_institution()
    count_result = MagicMock()
    count_result.scalar.return_value = 1
    data_result = MagicMock()
    data_result.scalars.return_value.all.return_value = [inst]
    mock_session.execute = AsyncMock(side_effect=[count_result, data_result])

    response = client.get("/api/v1/institutions")

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert len(body["items"]) == 1


@pytest.mark.parametrize("params", [("limit", 0), ("limit", 101), ("offset", -1)])
def test_list_institutions_pagination_bounds_are_enforced(
    client, mock_session, params
):
    """Out-of-bound limit/offset values are rejected with HTTP 422."""
    key, value = params
    response = client.get(f"/api/v1/institutions?{key}={value}")
    assert response.status_code == 422


def test_list_institutions_search_is_case_insensitive(client, mock_session):
    """Search matches case-insensitively against name/identifier fields."""
    inst = _make_institution(name="National Institute of Technology")

    count_result = MagicMock()
    count_result.scalar.return_value = 1
    data_result = MagicMock()
    data_result.scalars.return_value.all.return_value = [inst]
    mock_session.execute = AsyncMock(side_effect=[count_result, data_result])

    response = client.get("/api/v1/institutions?search=nAtIoNaL")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["name"] == "National Institute of Technology"

    # The search predicate is a case-insensitive database predicate (ILIKE).
    # Compile with the PostgreSQL dialect so .ilike() renders as the native
    # ILIKE operator (the default dialect emits LOWER(...) LIKE LOWER(...)
    # instead, which contains no literal "ilike").
    data_stmt = str(
        mock_session.execute.call_args_list[1][0][0].compile(
            dialect=postgresql.dialect()
        )
    )
    assert "ilike" in data_stmt.lower()


def test_list_institutions_search_no_match(client, mock_session):
    """A search that matches nothing returns an empty page."""
    count_result = MagicMock()
    count_result.scalar.return_value = 0
    data_result = MagicMock()
    data_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(side_effect=[count_result, data_result])

    response = client.get("/api/v1/institutions?search=zzz-no-match-institution")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


# --------------------------------------------------------------------------- #
# GET /institutions/{institution_id}
# --------------------------------------------------------------------------- #

def test_get_institution_by_id(client, mock_session):
    """Existing UUID returns the institution with HTTP 200."""
    inst = _make_institution()
    result = MagicMock()
    result.scalars.return_value.first.return_value = inst
    mock_session.execute.return_value = result

    response = client.get(f"/api/v1/institutions/{inst.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == inst.id
    assert body["name"] == inst.name
    assert body["normalized_name"] == inst.normalized_name


def test_get_institution_unknown_id_returns_404(client, mock_session):
    """Unknown UUID returns HTTP 404 with a generic message."""
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = result

    response = client.get(f"/api/v1/institutions/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Institution not found."


def test_get_institution_invalid_uuid_returns_422(client, mock_session):
    """A non-UUID path parameter is rejected with HTTP 422."""
    response = client.get("/api/v1/institutions/not-a-valid-uuid")
    assert response.status_code == 422