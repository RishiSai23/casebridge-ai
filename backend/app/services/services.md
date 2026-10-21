# Services Directory (`backend/app/services/`)

## A. Purpose
The `backend/app/services/` directory is dedicated to the business logic layer, AI-assisted complaint matching algorithms, overlap detection workflows, notification triggers, and coordination orchestration for CaseBridge AI.

## B. Directory tree
```
backend/app/services/
├── __init__.py            # Makes services a Python package
├── case_lifecycle.py      # Complaint status transition policy and append-only CaseEvent recording
└── services.md            # Navigation documentation for application services
```

## C. File inventory
| File | Responsibility |
|---|---|
| `__init__.py` | Marks `services` as a Python package. |
| `case_lifecycle.py` | Centralises permitted `CaseStatus` transitions (`ALLOWED_TRANSITIONS`), `closed_at` management for terminal states, and transactional `CaseEvent` staging via `record_case_event`. |
| `services.md` | Documents the business logic layer, AI service contracts, and development guidelines. |

## D. Subdirectory inventory
There are currently no subdirectories in `backend/app/services/`.

## E. Relationships and dependencies
- Sits between the API routing layer ([app/api/](../api/api.md)) and the persistence layer ([app/db/](../db/db.md)).
- `case_lifecycle.py` is consumed by [app/api/v1/complaints.py](../api/v1/complaints.py) for PATCH validation and event logging on create/update.
- Future modules will implement AI similarity matching, canonical case ordering, assignment/transfer workflows, and cross-bureau coordination.
- Consumes configuration thresholds (e.g. `AI_SIMILARITY_THRESHOLD`) from [app/core/config.py](../core/config.py).

## F. Development and verification
Lifecycle service unit tests: [backend/tests/test_case_lifecycle.py](../../tests/test_case_lifecycle.py).

Complaint API integration (mocked session): [backend/tests/test_case_events.py](../../tests/test_case_events.py).

```powershell
pytest tests/test_case_lifecycle.py tests/test_case_events.py -v
```

## G. Maintenance notes
- Keep business logic inside service classes/functions rather than embedding SQL queries or AI logic inside route handlers.
- Critical regulatory invariant: AI similarity scores are suggestions and must generate `potential` relationships; human review is required before any relationship becomes `confirmed` or `dismissed`.
- Service methods must perform explicit transaction handling or let route dependencies manage commit boundaries cleanly.
- Status transition rules live in `ALLOWED_TRANSITIONS` inside `case_lifecycle.py`; update tests in `test_case_lifecycle.py` when the policy changes.
