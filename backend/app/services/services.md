# Services Directory (`backend/app/services/`)

## A. Purpose
The `backend/app/services/` directory is dedicated to the business logic layer, AI-assisted complaint matching algorithms, overlap detection workflows, notification triggers, and coordination orchestration for CaseBridge AI.

## B. Directory tree
```
backend/app/services/
├── __init__.py            # Makes services a Python package
└── services.md            # Navigation documentation for application services
```

## C. File inventory
| File | Responsibility |
|---|---|
| `__init__.py` | Marks `services` as a Python package. |
| `services.md` | Documents the business logic layer, AI service contracts, and development guidelines. |

## D. Subdirectory inventory
There are currently no subdirectories in `backend/app/services/`.

## E. Relationships and dependencies
- Sits between the API routing layer ([app/api/](../api/api.md)) and the persistence layer ([app/db/](../db/db.md)).
- Will implement AI similarity matching, canonical case ordering, event logging, and cross-bureau coordination workflows.
- Consumes configuration thresholds (e.g. `AI_SIMILARITY_THRESHOLD`) from [app/core/config.py](../core/config.py).

## F. Development and verification
Services will be verified via dedicated unit and integration tests located in [backend/tests/](../../tests/tests.md).

## G. Maintenance notes
- Keep business logic inside service classes/functions rather than embedding SQL queries or AI logic inside route handlers.
- Critical regulatory invariant: AI similarity scores are suggestions and must generate `potential` relationships; human review is required before any relationship becomes `confirmed` or `dismissed`.
- Service methods must perform explicit transaction handling or let route dependencies manage commit boundaries cleanly.
