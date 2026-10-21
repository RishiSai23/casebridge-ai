# Backend Tests Directory (`backend/tests/`)

## A. Purpose
The `backend/tests/` directory contains automated unit, integration, and contract tests for the CaseBridge AI FastAPI backend. It verifies API endpoints, schema validation, data integrity rules, ORM models, and service layer behaviors.

## B. Directory tree
```
backend/tests/
├── __init__.py                   # Makes tests a Python package
├── test_bureau_schema.py         # Validates BureauCreate schema: uppercase/trimmed code, blank code/name rejected
├── test_case_relationship_schema.py # Validates CaseRelationshipCreate: self-relationships and extra fields rejected
├── test_complaint_case_endpoints.py  # Mocked Complaint Case API endpoint tests (POST, GET list, GET by ID, PATCH)
├── test_complaint_case_schema.py   # Validates ComplaintCaseCreate/Update/Read/List schemas
├── test_health.py                # Tests for /api/v1/health liveness only
├── test_institution_endpoints.py # Mocked Institution API endpoint tests (POST, GET list, GET by ID)
├── test_institution_schema.py    # Validates InstitutionCreate schema: trimmed name, untrusted normalized_name
├── test_models.py        # Tests for SQLAlchemy metadata completeness and Pydantic schemas
└── tests.md              # Navigation documentation for the backend/tests directory
```

## C. File inventory
| File | Responsibility |
|---|---|
| `__init__.py` | Marks `tests` as a Python package. |
| `test_bureau_schema.py` | Validates the `BureauCreate` Pydantic schema: bureau code is uppercased and trimmed, and blank or whitespace-only code/name values are rejected. |
| `test_case_relationship_schema.py` | Validates the `CaseRelationshipCreate` schema: valid relationship payloads succeed, self-relationships (same case on both sides) are rejected, and extra fields such as `confidence_score` are forbidden on creation. |
| `test_complaint_case_endpoints.py` | Mocked endpoint tests for the Complaint Case API (`POST`, paginated/filtered `GET`, `GET` by ID, `PATCH`) covering 201/200/404/409/422 responses, `closed_at` transitions on close/reopen/withdraw, and integrity-conflict rollback, using a mocked async session with no live database. |
| `test_complaint_case_schema.py` | Validates `ComplaintCaseCreate`, `ComplaintCaseUpdate`, `ComplaintCaseRead`, and `ComplaintCaseList`: subject/reference trimming, blank rejection, timezone-aware datetime enforcement, partial-update and explicit-null semantics, protected-field immutability, enum validation, and pagination bounds. |
| `test_health.py` | Validates API liveness (`200 OK`). Readiness-probe degraded/ready reporting is covered deterministically by `test_health_endpoints.py` via mocked database connectivity. |
| `test_institution_endpoints.py` | Mocked endpoint tests for the Institution API (`POST`, paginated/searched `GET`, `GET` by ID) covering 201/200/404/422 responses, case-insensitive `ILIKE` search, and duplicate-identifier conflicts, using a mocked async session with no live database. |
| `test_institution_schema.py` | Validates the `InstitutionCreate` schema: name trimming, blank-name rejection, and that client-supplied `normalized_name` is neither trusted nor exposed. |
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
