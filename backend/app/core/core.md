# Core Configuration Directory (`backend/app/core/`)

## A. Purpose
The `backend/app/core/` directory contains global application configuration, environment variable management, and central cross-cutting primitives for CaseBridge AI.

## B. Directory tree
```
backend/app/core/
├── __init__.py            # Makes core a Python package
├── config.py              # Central Pydantic BaseSettings application configuration
└── core.md                # Navigation documentation for the core directory
```

## C. File inventory
| File | Responsibility |
|---|---|
| `__init__.py` | Marks `core` as a Python package. |
| `config.py` | Defines `Settings` using Pydantic Settings, parses `.env` files, validates environment variables, and provides the cached `get_settings()` singleton. |
| `core.md` | Documents the core configuration management, environment variables, and zero-side-effect loading conventions. |

## D. Subdirectory inventory
There are currently no subdirectories in `backend/app/core/`.

## E. Relationships and dependencies
- Imported throughout the application:
  - In [app/main.py](../main.py) for application metadata and CORS origin configuration.
  - In [app/db/session.py](../db/session.py) for PostgreSQL connection parameters.
  - In [alembic/env.py](../../alembic/env.py) for schema migration connection credentials.
  - In [app/api/v1/health.py](../api/v1/health.py) for environment and version reporting.
- Must remain lightweight and free of heavy runtime dependencies (e.g., no database drivers, heavy ML packages, or network calls at import time).

## F. Development and verification
Verified by configuration tests in [backend/tests/test_health.py](../../tests/test_health.py) and via Python import check:
```powershell
python -c "from app.core.config import get_settings; s = get_settings(); print(s.APP_NAME, s.APP_VERSION)"
```

## G. Maintenance notes
- Keep `config.py` zero-side-effect: importing `config` must never initialize a network connection or start background workers.
- Always provide safe defaults for local development while requiring explicit environment variables for sensitive deployment values.
- In unit tests where environment variables are overridden, call `get_settings.cache_clear()` to reset cached singleton settings.
