"""
Unit tests for API health endpoints.
"""

from fastapi.testclient import TestClient

from app.core.config import get_settings
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


def test_health_readiness_no_database() -> None:
    """Test GET /api/v1/health/ready reports degraded when DATABASE_URL is empty."""
    settings = get_settings()
    # If DATABASE_URL is empty in test environment, expect degraded 503
    if not settings.DATABASE_URL:
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert "database" in data["checks"]
    else:
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
