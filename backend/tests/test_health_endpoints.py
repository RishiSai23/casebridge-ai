"""
Regression tests for the FastAPI health endpoints.

Endpoints under test
--------------------
GET /api/v1/health        — liveness probe (always 200 when the process is alive)
GET /api/v1/health/ready  — readiness probe (200 ready / 503 degraded)

Mocking strategy
----------------
The readiness route calls ``get_engine()`` directly (not via FastAPI ``Depends``),
so ``app.dependency_overrides`` cannot intercept it.  Instead we patch
``app.api.v1.health.get_engine`` with ``unittest.mock``:

* database reachable  -> mock engine whose ``connect()`` yields a working conn
* database unreachable -> mock engine whose conn ``execute()`` raises SQLAlchemyError
* DATABASE_URL missing -> patched get_engine raises ValueError

The liveness route never touches the database, so it always returns 200.

Test isolation
--------------
* ``get_settings.cache_clear()`` runs before/after every test so the lru_cache
  singleton cannot leak settings between tests.
* ``patch`` is used as a context manager, so mocks are restored automatically.
* ``.env`` is never modified or relied upon.
* No PostgreSQL, network, or Ollama access is required.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import create_app


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> None:
    """Clear the lru_cache on get_settings before and after each test."""
    from app.core.config import get_settings

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



def test_health_liveness_returns_200(client: TestClient) -> None:
    """Liveness returns HTTP 200 with the expected response fields."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "CaseBridge AI"
    assert data["version"] == "0.1.0"
    assert data["environment"] == "development"
    assert "timestamp" in data


def test_health_readiness_returns_200_when_database_ok(client: TestClient) -> None:
    """Readiness returns HTTP 200 with status 'ready' when the DB query succeeds."""
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    mock_engine.connect.return_value = mock_cm

    with patch("app.api.v1.health.get_engine", return_value=mock_engine):
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] == "ok"
    assert "timestamp" in data


def test_health_readiness_returns_503_when_database_unavailable(
    client: TestClient,
) -> None:
    """Readiness returns HTTP 503 with status 'degraded' when the DB connection fails."""
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.execute.side_effect = SQLAlchemyError("connection failed")
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    mock_engine.connect.return_value = mock_cm

    with patch("app.api.v1.health.get_engine", return_value=mock_engine):
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["database"] == "database unavailable"


def test_health_readiness_returns_503_when_database_url_missing(
    client: TestClient,
) -> None:
    """Readiness returns HTTP 503 with 'DATABASE_URL not configured' when the URL is absent."""
    with patch(
        "app.api.v1.health.get_engine",
        side_effect=ValueError("DATABASE_URL is not configured"),
    ):
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["database"] == "DATABASE_URL not configured"


def test_health_liveness_stays_200_when_database_unavailable(
    client: TestClient,
) -> None:
    """Liveness remains HTTP 200 even when the database is unconfigured/unreachable."""
    with patch(
        "app.api.v1.health.get_engine",
        side_effect=ValueError("DATABASE_URL is not configured"),
    ):
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_health_readiness_does_not_expose_connection_details(
    client: TestClient,
) -> None:
    """Failure responses sanitize the underlying database error (no credentials/URLs)."""
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    # A realistic driver error that contains credentials / connection info.
    mock_conn.execute.side_effect = SQLAlchemyError(
        "password authentication failed for user 'postgres'"
    )
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    mock_engine.connect.return_value = mock_cm

    with patch("app.api.v1.health.get_engine", return_value=mock_engine):
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["database"] == "database unavailable"

    body = response.text
    assert "password" not in body.lower()
    assert "postgres" not in body
    assert "DATABASE_URL" not in body



@pytest.fixture
def client() -> TestClient:
    """A TestClient against a fresh application instance."""
    return TestClient(create_app())
