"""
Unit tests for API health endpoints.

Readiness-probe behaviour (degraded/ready when the database is unreachable,
reachable, or unconfigured) is covered deterministically in
``test_health_endpoints.py`` by mocking ``app.api.v1.health.get_engine``.  This
file therefore retains only the liveness probe, which never touches the
database.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_liveness() -> None:
    """Test GET /api/v1/health returns 200 with application status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "CaseBridge AI"
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data
