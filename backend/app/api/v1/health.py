"""
Health-check route handlers.

Endpoints
---------
GET /api/v1/health
    Liveness probe — confirms the API process is alive.

GET /api/v1/health/ready
    Readiness probe — checks whether critical subsystems (currently: database
    URL configuration) are reachable.  Returns HTTP 200 with status="ready"
    when all checks pass, or HTTP 503 with status="degraded" when any check
    fails.  The individual check results are always included in the body so
    the caller can see exactly what failed.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=HealthResponse,
    summary="Liveness probe",
    description=(
        "Returns HTTP 200 with a small JSON payload whenever the API process "
        "is running.  Use this endpoint as a simple liveness check."
    ),
)
def health_liveness() -> HealthResponse:
    """Return application identity and current UTC timestamp."""
    settings = get_settings()
    return HealthResponse(
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        timestamp=datetime.now(tz=timezone.utc),
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description=(
        "Checks whether the application's critical subsystems are reachable. "
        "Returns HTTP 200 with status='ready' when all checks pass, or HTTP 503 "
        "with status='degraded' when any check fails.  Individual check results "
        "are always present in the response body."
    ),
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ReadinessResponse,
            "description": "One or more subsystems are unavailable.",
        }
    },
)
def health_readiness(response: Response) -> ReadinessResponse:
    """Run lightweight readiness checks and return an aggregated result.

    Current checks
    --------------
    database
        Verifies that DATABASE_URL is configured (non-empty).  An actual
        connection attempt will be added in the database integration task.
    """
    settings = get_settings()
    checks: dict[str, str] = {}

    # --- database check -------------------------------------------------
    # Phase 1: confirm the URL is configured.
    # Phase 2 (future): attempt a lightweight async ping to the DB.
    if settings.DATABASE_URL:
        checks["database"] = "ok"
    else:
        checks["database"] = "DATABASE_URL not configured"

    # Derive overall status from individual check results.
    overall: str = (
        "ready" if all(v == "ok" for v in checks.values()) else "degraded"
    )

    if overall == "degraded":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status=overall,  # type: ignore[arg-type]
        checks=checks,
        timestamp=datetime.now(tz=timezone.utc),
    )
