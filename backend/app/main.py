"""
FastAPI application factory.

This module creates and configures the FastAPI application instance.
It is the entry point that Uvicorn/Gunicorn will import.

Design principles
-----------------
* Configuration is read from app.core.config — never from os.environ directly.
* No database connection is established at module import time.
* CORS allowed-origins come from the CORS_ORIGINS environment variable so the
  frontend team can update them without touching source code.
* The versioned router is mounted once; future API versions add a new mount.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import get_settings

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Application factory
# --------------------------------------------------------------------------- #
def create_app() -> FastAPI:
    """Create, configure and return the FastAPI application.

    Using a factory function (rather than a bare module-level app object)
    makes it straightforward to create isolated instances for testing.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "Backend API for CaseBridge AI — an explainable complaint "
            "intelligence engine for AICTE's cross-bureau case monitoring "
            "dashboard (SIH 2026, Problem Statement 26264)."
        ),
        version=settings.APP_VERSION,
        # Serve OpenAPI docs only in non-production environments.
        docs_url="/docs" if settings.APP_ENV != "production" else None,
        redoc_url="/redoc" if settings.APP_ENV != "production" else None,
        openapi_url="/openapi.json" if settings.APP_ENV != "production" else None,
    )

    # ----------------------------------------------------------------------- #
    # CORS
    # ----------------------------------------------------------------------- #
    allowed_origins = settings.cors_origins_list
    logger.info("CORS allowed origins: %s", allowed_origins)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # ----------------------------------------------------------------------- #
    # Routers
    # ----------------------------------------------------------------------- #
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    # ----------------------------------------------------------------------- #
    # Startup / shutdown lifecycle hooks
    # ----------------------------------------------------------------------- #
    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info(
            "Starting %s v%s [env=%s]",
            settings.APP_NAME,
            settings.APP_VERSION,
            settings.APP_ENV,
        )

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        logger.info("Shutting down %s", settings.APP_NAME)

    return app


# --------------------------------------------------------------------------- #
# Application instance — imported by Uvicorn
# --------------------------------------------------------------------------- #
app = create_app()
