# Alembic Versions Directory (`backend/alembic/versions/`)

## A. Purpose
The `backend/alembic/versions/` directory stores versioned, linear database schema migration scripts for CaseBridge AI. Each script defines reversible database modifications (`upgrade()` and `downgrade()`) matching the SQLAlchemy domain models.

## B. Directory tree
```
backend/alembic/versions/
├── .gitkeep                                            # Preserves versions directory in git
├── 20261020_2f4e9a1b8c72_initial_domain_schema.py      # Initial schema revision establishing all 9 core domain tables
└── versions.md                                         # Navigation documentation for migration versions
```

## C. File inventory
| File | Responsibility |
|---|---|
| `.gitkeep` | Preserves the `versions/` directory structure in version control. |
| `20261020_2f4e9a1b8c72_initial_domain_schema.py` | Initial migration creating tables: `users`, `institutions`, `bureaus`, `complaint_cases`, `case_assignments`, `case_events`, `case_relationships`, `coordination_actions`, and `audit_logs` with all indexes and constraints. |
| `versions.md` | Documents migration scripts, version progression, and schema migration conventions. |

## D. Subdirectory inventory
There are no subdirectories in `backend/alembic/versions/`.

## E. Relationships and dependencies
- Executed by Alembic's migration engine configured in [backend/alembic/env.py](../env.py) and [backend/alembic.ini](../../alembic.ini).
- Defines schema structures mirroring the models defined in [backend/app/db/models/](../../app/db/models/models.md).
- Depends on PostgreSQL 16+ dialect features (`UUID`, `TIMESTAMP WITH TIME ZONE`, partial indexes).

## F. Development and verification
Check migration history without connecting to the database:
```powershell
alembic history --verbose
```
Preview migration SQL output for head revision:
```powershell
alembic upgrade head --sql
```
Apply migrations to a live PostgreSQL instance (when database container is running):
```powershell
alembic upgrade head
```

## G. Maintenance notes
- Never edit an already-applied migration script directly once merged; create a new revision using `alembic revision -m "description"`.
- Always verify both `upgrade()` and `downgrade()` pathways when authoring new migration scripts.
- Ensure partial indexes and unique constraints match domain invariants (e.g. unique active assignments per case, canonical relationship pair ordering).
