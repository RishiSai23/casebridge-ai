"""
Pydantic schemas for the health-check endpoints.

These are the canonical response shapes that the frontend team should
integrate against.  Keep them in sync with the route implementations in
app/api/v1/health.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response body for GET /api/v1/health."""

    status: Literal["ok"] = Field(
        default="ok",
        description="Always 'ok' when the API process is running.",
    )
    app: str = Field(description="Human-readable application name.")
    version: str = Field(description="Application version string (semver).")
    environment: str = Field(
        description="Deployment environment: development | staging | production."
    )
    timestamp: datetime = Field(
        description="UTC timestamp of when this response was generated.",
    )

    model_config = {"json_schema_extra": {"example": {
        "status": "ok",
        "app": "CaseBridge AI",
        "version": "0.1.0",
        "environment": "development",
        "timestamp": "2026-10-20T05:16:30.123456Z",
    }}}


class ReadinessResponse(BaseModel):
    """Response body for GET /api/v1/health/ready."""

    status: Literal["ready", "degraded"] = Field(
        description="'ready' if all critical subsystems are reachable, 'degraded' otherwise.",
    )
    checks: dict[str, str] = Field(
        description=(
            "Map of subsystem name to its check result: 'ok' or a short error message."
        ),
    )
    timestamp: datetime = Field(
        description="UTC timestamp of when this response was generated.",
    )

    model_config = {"json_schema_extra": {"example": {
        "status": "ready",
        "checks": {"database": "ok"},
        "timestamp": "2026-10-20T05:16:30.123456Z",
    }}}
