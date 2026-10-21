# CaseBridge AI — Autonomous Agent Navigation & Operating Protocol

**Primary Entry Point for AI Agents and Developers**

---

## 1. Project Context & Purpose

**Project Name:** CaseBridge AI  
**SIH 2026 Problem Statement ID:** 26264  
**Problem Statement:** Integrated Dashboard for Monitoring and Tracking Institution-Related Complaint Cases Across AICTE Bureaus/Cells.

### Executive Overview
AICTE receives grievances and complaints regarding technical education institutions across disparate bureaus and cells (including the Regulation Bureau [RB], Public Grievance Redressal Cell [PGRC], Legal Cell, Approval Bureau, etc.). Without centralized coordination, cases involving the same institution suffer from duplicated effort, conflicting or overlapping regulatory actions, untracked ownership, and communication delays.

**CaseBridge AI** provides an explainable AI-assisted multi-bureau intelligence and tracking platform that:
- Centralizes educational institution profiles and links complaints via unique AICTE identifiers and normalized institutional names.
- Tracks full complaint lifecycles, bureau ownership assignments, chronological event history, and inter-bureau coordination actions.
- Automatically flags cross-bureau case overlap and potential duplicates using explainable semantic similarity and category matching.
- **Enforces Human-in-the-Loop Review:** AI similarity scores produce *suggestions* (`potential` relationships). Two complaints involving the same institution or subject are **never** autonomously merged or concluded without an officer's explicit verification (`confirmed` or `dismissed`).
- Delivers real-time analytics, ageing metrics, resolution alerts, and administrative management reports.

Authoritative progress and submission readiness are tracked in [progress.md](progress.md).

---

## 2. Current Verified Project Status

| Area | Verified State | Notes |
|---|---|---|
| **Repository Intelligence & Navigation** | Verified | Complete directory Markdown navigation system, automated validator (`scripts/validate_navigation.py`), root `AGENTS.md`, and `progress.md`. |
| **Backend Core & Health Probes** | Verified | FastAPI application factory, CORS middleware, Pydantic BaseSettings, `/api/v1/health` (liveness), and `/api/v1/health/ready` (readiness). |
| **Relational Database Domain Models** | Verified | Complete SQLAlchemy 2.0 ORM models for all 9 domain entities: `users`, `institutions`, `bureaus`, `complaint_cases`, `case_assignments`, `case_events`, `case_relationships`, `coordination_actions`, and `audit_logs`. |
| **Schema Migrations (Alembic)** | Verified | Initial migration `20261020_2f4e9a1b8c72_initial_domain_schema.py` committed and verified via `alembic history`. |
| **Automated Tests** | Verified (7 passed historical; user-reported: 120 tests passed) | Pytest test suite covering health probes, metadata registration completeness, and Pydantic schema validation; tests have not been re-executed since merge `6dd0d08`. User-reported: backend test suite passed with 120 tests, and navigation validator passed (`python scripts/validate_navigation.py`). Results reported by the user, not executed by this agent. |
| **Local PostgreSQL Database** | Docker Compose configured | `docker-compose.yml` for PostgreSQL 16 ready; container startup requires Docker Desktop runtime. |
| **Domain CRUD Endpoints & Services** | In Progress (partial) | Institution CRUD (`POST`, `GET` list, `GET` by ID) and complaint case CRUD (`POST`, `GET` list, `GET` by ID, `PATCH`) implemented and mounted in `router.py`; service layer (`app/services/`) empty; bureau, relationship, and coordination APIs not yet implemented. |
| **Frontend Application** | External / Planned | Planned for integration under `frontend/` by team members. |

---

## 3. Mandatory Repository Navigation Rules

Every AI agent working on this repository **must** adhere to these navigation rules:

1. **Start at `AGENTS.md`:** Review the architecture, current verified status, and conventions before inspecting or modifying code.
2. **Consult `progress.md`:** Check the authoritative progress checklist to align with current priorities and acceptance criteria.
3. **Read Directory Documentation Before Modification:** Every directory contains a `<dirname>.md` file detailing its responsibilities, child inventories, dependencies, and maintenance guidelines:
   - When modifying files in `backend/`, read [backend/backend.md](backend/backend.md).
   - When modifying files in `backend/app/`, read [backend/app/app.md](backend/app/app.md).
   - When modifying files in `backend/app/db/models/`, read [backend/app/db/models/models.md](backend/app/db/models/models.md).
   - When modifying scripts, read [scripts/scripts.md](scripts/scripts.md).
4. **Maintain Directory Markdown Synchronization:** Whenever a file or directory is added, renamed, moved, or deleted, update the parent directory's Markdown file and run the validation script:
   ```powershell
   python scripts/validate_navigation.py
   ```
5. **No Undocumented Files:** A newly created source file must never be left undocumented in its parent's Markdown inventory.

---

## 4. Top-Level Repository Structure

```
casebridge-ai/
├── AGENTS.md                  # This primary autonomous agent operating protocol
├── docker-compose.yml         # Local PostgreSQL 16 service definition
├── progress.md                # Authoritative progress and SIH submission readiness tracker
├── README.md                  # High-level project README and local docker guide
├── backend/                   # Python FastAPI backend service
│   ├── backend.md             # Backend navigation documentation
│   ├── alembic/               # Alembic database migrations
│   ├── app/                   # FastAPI application source code
│   └── tests/                 # Automated test suite
└── scripts/                   # Repository maintenance, audit, and CI automation scripts
    ├── scripts.md             # Scripts directory navigation documentation
    └── validate_navigation.py # Automated navigation & documentation integrity checker
```

### Direct Navigation Links

| Path | Type | Navigation Document | Description |
|---|---|---|---|
| `backend/` | Directory | [backend/backend.md](backend/backend.md) | Asynchronous FastAPI service, SQLAlchemy ORM models, Alembic migrations, and automated test suite. |
| `scripts/` | Directory | [scripts/scripts.md](scripts/scripts.md) | Maintenance and repository integrity validation utilities. |
| `docker-compose.yml` | File | — | PostgreSQL 16 container definition with health check and persistent named volume. |
| `progress.md` | File | [progress.md](progress.md) | Authoritative SIH submission and implementation progress tracker. |
| `README.md` | File | [README.md](README.md) | Project introduction and database startup commands. |

### Documented Exclusions
The following generated and cache directories are excluded from manual documentation:
- `.git/` (Git version control internals)
- `__pycache__/` (Python compiled bytecode caches)
- `.pytest_cache/` (Pytest test execution caches)
- `.venv/` / `venv/` (Local Python virtual environments)
- `node_modules/` (Frontend package dependencies when added)

---

## 5. Verified Technology Stack & Architecture

- **Backend Framework:** FastAPI (`>=0.115,<0.116`) running on Python 3.10+
- **ASGI Server:** Uvicorn (`>=0.32,<0.33`)
- **Database & ORM:** PostgreSQL 16, SQLAlchemy 2.0 (`>=2.0,<3.0`) with `asyncpg` (`>=0.30,<1.0`)
- **Database Migrations:** Alembic (`>=1.14,<2.0`) with async engine integration
- **Configuration & Validation:** Pydantic v2 (`>=2.9,<3.0`), `pydantic-settings` (`>=2.6,<3.0`), `python-dotenv`
- **Testing:** Pytest (`>=9.0`), `httpx` (`TestClient`)

### Key Architectural Invariants
1. **Lazy Database Engine:** The FastAPI application starts and serves liveness health checks even if the database is offline or unconfigured (`DATABASE_URL` empty).
2. **Strict UTC Timestamps:** All database timestamps use `TIMESTAMP WITH TIME ZONE` and PostgreSQL `server_default=func.now()` to avoid clock-drift across server instances.
3. **Canonical Relationship Ordering:** In `case_relationships`, `source_case_id < target_case_id` is enforced by database CHECK constraints to prevent duplicate reciprocal pairs `(A, B)` and `(B, A)`.
4. **Append-Only Case Events:** `CaseEvent` is an append-only timeline table. Events are never updated or mutated.
5. **Partial Unique Indexes:** `institutions.aicte_institution_id` enforces uniqueness across non-null external identifiers. `case_assignments` enforces that each complaint case has at most one active bureau assignment.
6. **Human Review Exclusivity:** The AI engine computes `confidence_score` and creates `potential` links. Only human reviewers are authorized to transition a relationship to `confirmed` or `dismissed`.

---

## 6. Development, Testing, and Verification Commands

### Run Navigation Validator
```powershell
python scripts/validate_navigation.py
```

### Run Backend Automated Tests
```powershell
cd backend
pytest -v
```

### Run Backend Development Server
```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive OpenAPI documentation will be accessible at: `http://localhost:8000/docs`

### Check Alembic Database Migrations
```powershell
cd backend
alembic history --verbose
alembic upgrade head --sql
```

### Start Local PostgreSQL (Docker)
```powershell
docker compose up -d postgres
docker compose ps
```

---

## 7. Rules for Modifying the Repository

### Adding New Files
1. Identify the target directory.
2. Create the file adhering to project formatting and architecture.
3. Open the directory's `<dirname>.md` file and add a single-line inventory entry.
4. If a new directory is created:
   - Create `<dirname>/<dirname>.md` with all 7 standard sections (A through G).
   - Update the parent directory's Subdirectory Inventory with a relative link.
5. Run `python scripts/validate_navigation.py` to confirm zero broken links or missing entries.

### Modifying Files
- Update the file description in `<dirname>.md` if its purpose or contract changed.
- Update `progress.md` if the change advances or alters a deliverable's verified status.
- Never modify public API contracts or database constraints without updating the corresponding schemas and migrations.

### Deleting or Renaming Files
- Remove the file entry from the parent directory's Markdown inventory.
- Update all internal imports, navigation links, and references across the codebase.
- Verify with `python scripts/validate_navigation.py`.

---

## 8. Debugging, Testing & Security Standards

- **Evidence-Based Debugging:** Reproduce bugs using test cases in `backend/tests/`. Never suppress validation or weaken security constraints just to make a test pass.
- **Data Protection & Mock Data:** Never log or commit real complainant personal data, credentials, or private API keys. Use synthetic demonstration fixtures.
- **Negative Testing:** Always test boundary conditions, invalid inputs, duplicate registrations, and unauthorized state transitions.

---

## 9. Mandatory End-of-Task Checklist

Before declaring any task complete, every agent must verify:
- [ ] Code changes follow existing architectural conventions and pass relevant unit/integration tests (`pytest -v`).
- [ ] Root `AGENTS.md` and `progress.md` reflect current verified state.
- [ ] Every modified or created directory has an up-to-date `<dirname>.md`.
- [ ] Every new file is described in its parent directory's file inventory.
- [ ] All relative Markdown links resolve correctly.
- [ ] Automated validation check passes without errors:
  ```powershell
  python scripts/validate_navigation.py
  ```
- [ ] The final response includes a structured report covering Summary, Files Changed, Verification, Progress Status, Documentation Audit, Remaining Risks, and Next Recommended Task.
