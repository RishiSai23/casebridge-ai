# Backend Root Directory (`backend/`)

## A. Purpose
The `backend/` directory contains the complete Python backend service for CaseBridge AI. It provides an asynchronous FastAPI REST API, SQLAlchemy 2.0 ORM persistence, Alembic schema migrations, Pydantic v2 validation contracts, and automated testing suites for the AICTE complaint monitoring platform.

## B. Directory tree
```
backend/
├── .env.example           # Example environment variable file for local development
├── alembic.ini            # Alembic database migration tool configuration
├── backend.md             # Navigation documentation for the backend directory
├── migration_preview.sql  # SQL DDL preview of the initial Alembic migration (revision 2f4e9a1b8c72)
├── README.md              # Backend setup guide, architecture notes, and API documentation
├── requirements.txt       # Direct Python dependencies with pinned minor versions
├── alembic/               # Database migrations, environment runner, and version scripts
│   ├── alembic.md
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── app/                   # FastAPI application source code
│   ├── app.md
│   ├── main.py
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── schemas/
│   └── services/
└── tests/                 # Automated pytest unit and integration test suite
    ├── tests.md
    ├── test_health.py
    └── test_models.py
```

## C. File inventory
| File | Responsibility |
|---|---|
| `.env.example` | Template environment configuration file specifying database URL, CORS origins, and AI matching parameters. |
| `alembic.ini` | Global configuration file for Alembic database migrations. |
| `backend.md` | Documents the backend component structure, dependencies, workflows, and navigation. |
| `migration_preview.sql` | SQL DDL preview of the initial Alembic migration (`alembic upgrade head --sql`) for revision `2f4e9a1b8c72`: `BEGIN;`/`COMMIT;`-wrapped `CREATE TABLE` statements for all domain tables with indexes (including partial unique indexes), column comments, and check constraints, ending with an `INSERT` seeding `alembic_version` with revision `2f4e9a1b8c72`. |
| `README.md` | Detailed architectural documentation, design decisions, entity relationships, and setup commands. |
| `requirements.txt` | Lists direct Python dependencies (FastAPI, SQLAlchemy, asyncpg, Alembic, Pydantic, etc.) pinned by minor version. |

## D. Subdirectory inventory
| Subdirectory | Navigation Document | Responsibility |
|---|---|---|
| `alembic/` | [alembic/alembic.md](alembic/alembic.md) | Database migration runner and revision version history scripts. |
| `app/` | [app/app.md](app/app.md) | Main application package with API routes, settings, database models, and schemas. |
| `tests/` | [tests/tests.md](tests/tests.md) | Pytest test suite covering endpoints, domain schemas, and ORM metadata. |

## E. Relationships and dependencies
- Exposes REST API endpoints consumed by the frontend application (CORS configured via `CORS_ORIGINS`).
- Connects asynchronously to PostgreSQL (configured via root [docker-compose.yml](../docker-compose.yml) or cloud DB).
- Uses `alembic` to apply relational migrations to the database.

## F. Development and verification
Install dependencies:
```powershell
pip install -r requirements.txt
```
Run tests:
```powershell
pytest -v
```
Start development server:
```powershell
uvicorn app.main:app --reload --port 8000
```
Check migration history:
```powershell
alembic history --verbose
```

## G. Maintenance notes
- Dependencies in `requirements.txt` should pin `major.minor` to allow security updates within the minor version without breaking builds.
- Never commit actual `.env` files or secret credentials to version control.
- Ensure any new database models are added to `app/db/models/__init__.py` and covered by migration scripts before deployment.
