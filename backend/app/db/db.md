# Database Layer Directory (`backend/app/db/`)

## A. Purpose
The `backend/app/db/` directory encapsulates database session lifecycle management, async engine initialization, connection pooling, and the ORM domain models for CaseBridge AI.

## B. Directory tree
```
backend/app/db/
├── __init__.py            # Makes db a Python package
├── db.md                  # Navigation documentation for the db directory
├── session.py             # Async engine, sessionmaker, and get_db FastAPI dependency
└── models/                # SQLAlchemy domain model definitions
    ├── __init__.py
    ├── audit_log.py
    ├── base.py
    ├── bureau.py
    ├── case_assignment.py
    ├── case_event.py
    ├── case_relationship.py
    ├── complaint_case.py
    ├── coordination_action.py
    ├── enums.py
    ├── institution.py
    ├── models.md
    └── user.py
```

## C. File inventory
| File | Responsibility |
|---|---|
| `__init__.py` | Marks `db` as a Python package. |
| `db.md` | Documents the database connection lifecycle, session management, and model architecture. |
| `session.py` | Implements lazy async engine initialization, `async_sessionmaker`, and the `get_db` FastAPI request dependency. |

## D. Subdirectory inventory
| Subdirectory | Navigation Document | Responsibility |
|---|---|---|
| `models/` | [models/models.md](models/models.md) | Contains all SQLAlchemy 2.0 ORM domain entities, table schemas, constraints, and enumerations. |

## E. Relationships and dependencies
- Consumes database connection settings from [app/core/config.py](../core/config.py).
- Uses `SQLAlchemy 2.0` with the `asyncpg` async PostgreSQL driver.
- Injected into FastAPI route handlers via the `Depends(get_db)` pattern.
- Models are imported by [backend/alembic/env.py](../../alembic/env.py) for schema migrations.

## F. Development and verification
Verified by automated metadata tests in [backend/tests/test_models.py](../../tests/test_models.py):
```powershell
pytest tests/test_models.py -v
```

## G. Maintenance notes
- The engine in `session.py` is initialized lazily: importing `session` does not require an active database connection or fail when `DATABASE_URL` is empty.
- Always manage database transactions explicitly: `get_db` does not auto-commit on request completion.
- Configure `pool_pre_ping=True` to guarantee stale connections are pruned before usage.
