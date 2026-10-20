# Alembic Migration Directory (`backend/alembic/`)

## A. Purpose
The `backend/alembic/` directory contains configuration, runtime environment hooks, templates, and revision scripts for managing asynchronous relational database schema migrations for CaseBridge AI.

## B. Directory tree
```
backend/alembic/
├── alembic.md             # Navigation documentation for the alembic directory
├── env.py                 # Async migration runtime environment runner
├── script.py.mako         # Mako template used by Alembic to generate new revision files
└── versions/              # Directory containing versioned migration scripts
    ├── .gitkeep
    ├── 20261020_2f4e9a1b8c72_initial_domain_schema.py
    └── versions.md
```

## C. File inventory
| File | Responsibility |
|---|---|
| `alembic.md` | Documents the Alembic configuration, runtime scripts, and revision management conventions. |
| `env.py` | Migration runtime script that loads application configuration, imports all models for metadata discovery, and runs async migrations. |
| `script.py.mako` | Template file used by Alembic to render newly generated migration scripts. |

## D. Subdirectory inventory
| Subdirectory | Navigation Document | Responsibility |
|---|---|---|
| `versions/` | [versions/versions.md](versions/versions.md) | Contains linear, versioned schema migration scripts. |

## E. Relationships and dependencies
- Configured via [backend/alembic.ini](../alembic.ini).
- Reads database connection credentials dynamically from `DATABASE_URL` via [app/core/config.py](../app/core/config.py) rather than hardcoding credentials in configuration files.
- Automatically discovers SQLAlchemy metadata by importing [app.db.models](../app/db/models/models.md).

## F. Development and verification
View current revision history:
```powershell
alembic history --verbose
```
Generate dry-run SQL preview:
```powershell
alembic upgrade head --sql
```

## G. Maintenance notes
- `env.py` supports both offline (`--sql`) and online async migration modes using `create_async_engine`.
- Always ensure all new models are exported from `app/db/models/__init__.py` so that Alembic's autogenerate detects schema additions.
