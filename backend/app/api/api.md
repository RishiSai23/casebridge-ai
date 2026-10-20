# API Directory (`backend/app/api/`)

## A. Purpose
The `backend/app/api/` directory is the top-level HTTP routing root for the CaseBridge AI application. It organizes API endpoints into versioned namespaces, enabling smooth backwards compatibility and evolution of public REST APIs.

## B. Directory tree
```
backend/app/api/
├── __init__.py            # Makes api a Python package
├── api.md                 # Navigation documentation for the api directory
└── v1/                    # Version 1 API routes and endpoints
    ├── __init__.py
    ├── health.py
    ├── router.py
    └── v1.md
```

## C. File inventory
| File | Responsibility |
|---|---|
| `__init__.py` | Marks `api` as a Python package. |
| `api.md` | Documents the top-level API namespace architecture and routing standards. |

## D. Subdirectory inventory
| Subdirectory | Navigation Document | Responsibility |
|---|---|---|
| `v1/` | [v1/v1.md](v1/v1.md) | Contains all Version 1 endpoint routes, including health probes and domain resources. |

## E. Relationships and dependencies
- Mounted into the core FastAPI application in [app/main.py](../main.py).
- Versioned subdirectories import schemas from [app/schemas/](../schemas/schemas.md) and configuration from [app/core/config.py](../core/config.py).

## F. Development and verification
Run the API test suite from `backend/`:
```powershell
pytest tests/test_health.py -v
```

## G. Maintenance notes
- API versioning is mandatory for all public endpoints.
- If a future breaking API change is required, create a new sibling version directory (e.g. `v2/`) rather than altering existing v1 contracts without backwards-compatibility provisions.
