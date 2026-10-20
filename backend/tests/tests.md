# Backend Tests Directory (`backend/tests/`)

## A. Purpose
The `backend/tests/` directory contains automated unit, integration, and contract tests for the CaseBridge AI FastAPI backend. It verifies API endpoints, schema validation, data integrity rules, ORM models, and service layer behaviors.

## B. Directory tree
```
backend/tests/
├── __init__.py           # Makes tests a Python package
├── test_health.py        # Tests for /api/v1/health and /api/v1/health/ready
├── test_models.py        # Tests for SQLAlchemy metadata completeness and Pydantic schemas
└── tests.md              # Navigation documentation for the backend/tests directory
```

## C. File inventory
| File | Responsibility |
|---|---|
| `__init__.py` | Marks `tests` as a Python package. |
| `test_health.py` | Validates API liveness (`200 OK`) and readiness probe reporting (degraded when `DATABASE_URL` is unconfigured). |
| `test_models.py` | Asserts SQLAlchemy table metadata completeness and tests Pydantic schema validation rules. |
| `tests.md` | Documents the test directory structure, inventories, and testing workflows. |

## D. Subdirectory inventory
There are currently no subdirectories in `backend/tests/`.

## E. Relationships and dependencies
- Imports the FastAPI application factory from [app/main.py](../app/main.py).
- Imports database models from [app/db/models/](../app/db/models/models.md).
- Imports schemas and enums from [app/schemas/](../app/schemas/schemas.md) and [app/db/models/enums.py](../app/db/models/enums.py).
- Uses `pytest` as the test runner and `fastapi.testclient.TestClient` (backed by `httpx`) for synchronous HTTP execution.

## F. Development and verification
Run the test suite from `backend/`:
```powershell
pytest -v
```
Or run a specific test file:
```powershell
pytest tests/test_health.py -v
```

## G. Maintenance notes
- Maintain test isolation: tests should not depend on execution order.
- Do not hardcode database mutations in tests that run in environments without an active PostgreSQL container; use mocks or SQLite/async session fixtures when testing live database queries.
- Add negative test cases and boundary validation for every newly added schema or endpoint.
