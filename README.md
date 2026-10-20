# CaseBridge AI

**SIH 2026 — AICTE Problem Statement 26264**  
Integrated Dashboard for Monitoring and Tracking Institution-Related Complaint Cases Across AICTE Bureaus/Cells.

---

## Repository layout

```
casebridge-ai/
├── backend/   — Python/FastAPI REST API and AI intelligence engine
└── frontend/  — (team members' work — see their documentation)
```

## Quick links

- [Backend README](backend/README.md) — setup, configuration and API reference

---

## Local PostgreSQL (Docker Compose)

### Prerequisite

- Docker Desktop is installed and running.

### Configuration

The repository root includes a minimal PostgreSQL-only Compose file:

- Service: postgres
- Image: postgres:16
- Port mapping: 127.0.0.1:${POSTGRES_HOST_PORT:-5432}:5432
- Persistent volume: casebridge_postgres_data

Configurable Compose variables:

- POSTGRES_DB (default: casebridge_dev)
- POSTGRES_USER (default: casebridge_dev)
- POSTGRES_PASSWORD (default: change_me_local_dev)
- POSTGRES_HOST_PORT (default: 5432)

Backend connection string is configured through backend/.env (copied from backend/.env.example) and uses the async SQLAlchemy driver format:

- postgresql+asyncpg://USER:PASSWORD@localhost:PORT/DBNAME

### Start PostgreSQL

Run from repository root:

	docker compose up -d postgres

### Check status and health

Run from repository root:

	docker compose ps
	docker compose logs postgres

### Stop without deleting data

Run from repository root:

	docker compose stop postgres

### Remove container but keep named volume data

Run from repository root:

	docker compose down

### Destructive: remove containers and delete database data

WARNING: This deletes the named PostgreSQL volume and all local database data.

Run from repository root:

	docker compose down -v