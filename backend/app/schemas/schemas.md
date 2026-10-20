# Schemas Directory (`backend/app/schemas/`)

## A. Purpose
The `backend/app/schemas/` directory defines Pydantic v2 data models for request validation, serialization, response schemas, and API contracts across CaseBridge AI.

## B. Directory tree
```
backend/app/schemas/
├── __init__.py                # Makes schemas a Python package
├── bureau.py                  # Schemas for Bureau resources (create, read)
├── case_relationship.py       # Schemas for CaseRelationship resources and validation
├── complaint_case.py          # Schemas for ComplaintCase lifecycle and summaries
├── health.py                  # Schemas for health and readiness responses
├── institution.py             # Schemas for Institution resources (create, read, summary)
└── schemas.md                 # Navigation documentation for Pydantic schemas
```

## C. File inventory
| File | Responsibility |
|---|---|
| `__init__.py` | Marks `schemas` as a Python package. |
| `bureau.py` | Defines `BureauBase`, `BureauCreate`, and `BureauRead` schemas with uppercase code validation. |
| `case_relationship.py` | Defines `CaseRelationshipBase`, `CaseRelationshipCreate` (enforcing distinct cases), and `CaseRelationshipRead` schemas. |
| `complaint_case.py` | Defines `ComplaintCaseBase`, `ComplaintCaseCreate`, and `ComplaintCaseRead` schemas enforcing timezone-aware timestamps. |
| `health.py` | Defines `HealthResponse` and `ReadinessResponse` schemas for health endpoints. |
| `institution.py` | Defines `InstitutionBase`, `InstitutionCreate` (with whitespace stripping), `InstitutionRead`, and `InstitutionSummary` schemas. |
| `schemas.md` | Documents schema conventions, validation behaviors, and boundary isolation. |

## D. Subdirectory inventory
There are currently no subdirectories in `backend/app/schemas/`.

## E. Relationships and dependencies
- Enforces strict separation of concerns: ORM models from [app/db/models/](../db/models/models.md) are transformed to Pydantic schemas before returning to API clients.
- Uses domain enums from [app/db/models/enums.py](../db/models/enums.py).
- Imported by API route definitions in [app/api/](../api/api.md) for request validation and OpenAPI doc generation.

## F. Development and verification
Verified by automated schema validation tests in [backend/tests/test_models.py](../../tests/test_models.py):
```powershell
pytest tests/test_models.py -v
```

## G. Maintenance notes
- Keep `from_attributes = True` (`ConfigDict`) on read schemas to enable direct serialization from SQLAlchemy ORM instances.
- Never accept internal system-generated or AI-computed fields (such as `confidence_score` or server-derived timestamps) in client create/update schemas.
- Ensure strict datetime validation: all datetimes must be timezone-aware (UTC).
