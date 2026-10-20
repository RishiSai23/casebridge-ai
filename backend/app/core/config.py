"""
Application configuration.

Settings are loaded from environment variables (and optionally a .env file
via python-dotenv).  Pydantic's BaseSettings validates and coerces types at
startup, so misconfigured deployments fail loudly on launch rather than at
runtime.

Do NOT import heavy dependencies (database drivers, ML libraries) here.
This module must be importable with zero side-effects.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All application-level configuration.

    Every value has a safe local-development default.  Secrets (database
    credentials, API keys) must be supplied via environment variables or a
    local .env file that is excluded from version control.
    """

    model_config = SettingsConfigDict(
        # Load a .env file if present; silently skip if it doesn't exist.
        env_file=".env",
        env_file_encoding="utf-8",
        # Ignore extra keys in the environment so future variables can be
        # added without breaking older application versions.
        extra="ignore",
        # Use case-insensitive env-var matching.
        case_sensitive=False,
    )

    # ------------------------------------------------------------------ #
    # Application identity
    # ------------------------------------------------------------------ #
    APP_NAME: str = "CaseBridge AI"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"  # development | staging | production

    # ------------------------------------------------------------------ #
    # API
    # ------------------------------------------------------------------ #
    API_V1_PREFIX: str = "/api/v1"

    # ------------------------------------------------------------------ #
    # CORS
    # Comma-separated list of allowed origins.
    # Example: CORS_ORIGINS="http://localhost:3000,https://casebridge.example.com"
    # ------------------------------------------------------------------ #
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors(cls, v: object) -> object:
        """Accept either a raw comma-separated string or an already-parsed list."""
        return v  # returned as-is; splitting is done via the property below

    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS_ORIGINS as a deduplicated list of stripped strings."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # ------------------------------------------------------------------ #
    # Database (placeholder — not connected in Task 1)
    # ------------------------------------------------------------------ #
    DATABASE_URL: str = ""
    # e.g. postgresql+asyncpg://user:password@localhost:5432/casebridge

    # ------------------------------------------------------------------ #
    # AI / Matching engine (placeholder — not implemented in Task 1)
    # ------------------------------------------------------------------ #
    AI_SIMILARITY_THRESHOLD: float = 0.75
    # Minimum cosine similarity for two complaints to be flagged as related.
    AI_MAX_OVERLAP_CANDIDATES: int = 10
    # Maximum number of candidate matches returned per complaint.

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #
    LOG_LEVEL: str = "INFO"  # DEBUG | INFO | WARNING | ERROR | CRITICAL


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance.

    Using lru_cache means the .env file is read exactly once per process.
    In tests, call get_settings.cache_clear() before overriding settings.
    """
    return Settings()
