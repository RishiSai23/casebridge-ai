# Application Root Directory (`backend/app/`)

## A. Purpose
The `backend/app/` directory contains the complete source code of the CaseBridge AI FastAPI backend application, organized into clean modular layers: entry point, configuration, routing, persistence, domain schemas, and business services.

## B. Directory tree
```
backend/app/
├── __init__.py            # Makes app a Python package
├── app.md                 # Navigation documentation for the app directory
├── main.py                # FastAPI application factory and ASGI entrypoint
├── api/                   # REST API routes and versioned endpoints
│   ├── api.md
│   └── v1/
├── core/                  # Application configuration and settings
│   └── core.md
├── db/                    # SQLAlchemy engine, session management, and domain models
│   ├── db.md
│   └── models/
├── schemas/               # Pydantic v2 validation and serialization schemas
│   └── schemas.md
└── services/              # Business logic and AI matching services
    └── services.md
```

## C. File inventory
| File | Responsibility |
|---|---|
| `__init__.py` | Marks `app` as a Python package. |
| `app.md` | Documents the overall backend application structure, modular layering, and architecture. |
| `main.py` | FastAPI application factory (`create_app`), middleware configuration (CORS), OpenAPI documentation settings, and top-level router mounting. |

## D. Subdirectory inventory
| Subdirectory | Navigation Document | Responsibility |
|---|---|---|
| `api/` | [api/api.md](api/api.md) | HTTP REST API endpoints and versioned routers (`/api/v1`). |
| `core/` | [core/core.md](core/core.md) | Centralized Pydantic application configuration and environment settings. |
| `db/` | [db/db.md](db/db.md) | Database connection engine, session dependencies, and SQLAlchemy 2.0 ORM models. |
| `schemas/` | [schemas/schemas.md](schemas/schemas.md) | Pydantic v2 data models for API request validation and response serialization. |
| `services/` | [services/services.md](services/services.md) | Core domain business logic, AI matching engines, and regulatory workflow execution. |

## E. Relationships and dependencies
- Ingested by ASGI servers (Uvicorn/Gunicorn) targeting `app.main:app`.
- Reads application configuration from `app/core/config.py`.
- Integrates with PostgreSQL via `app/db/session.py`.
- Tested by automated test suites in [backend/tests/](../tests/tests.md).

## F. Development and verification
Run the development server locally from `backend/`:
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Run automated test suite:
```powershell
pytest -v
```

## G. Maintenance notes
- Maintain strict unidirectional dependencies: `api` -> `services` -> `db/models` & `schemas`.
- Never import database sessions or write SQL queries directly within route handlers.
- Keep `main.py` focused on app composition, middleware, and lifecycle handlers; do not define business routes directly in `main.py`.
