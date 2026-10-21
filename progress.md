# CaseBridge AI — Project Progress & SIH Submission Tracker

**Authoritative Checklist for Implementation and Submission Readiness**

---

## 1. Project Overview

- **Project Name:** CaseBridge AI
- **SIH Problem Statement ID:** 26264
- **Problem Statement:** Integrated Dashboard for Monitoring and Tracking Institution-Related Complaint Cases Across AICTE Bureaus/Cells.
- **Objective:** Eliminate multi-bureau grievance duplication, prevent uncoordinated regulatory actions, track case assignments across AICTE cells (Regulation Bureau, PGRC, etc.), and provide explainable AI-assisted case overlap detection with human review.
- **Submission Readiness Definition:** A production-grade, end-to-end demonstrable platform featuring:
  1. Centralized institution master data with AICTE identifiers.
  2. Full complaint lifecycle, assignment tracking, and append-only event histories.
  3. Explainable AI case overlap detection with strict human review workflows.
  4. Cross-bureau coordination action queues and deadline escalation.
  5. Multi-dimensional analytics, ageing metrics, and KPI dashboards.
  6. Verified backend APIs, database integrity, automated test suites, and reproducible demo scripts.

---

## 2. Current Verified Status

| Category | Status | Details |
|---|---|---|
| **Repository Intelligence & Navigation** | Complete (`100%`) | All directories documented with Markdown files; `scripts/validate_navigation.py` implemented; root `AGENTS.md` and `progress.md` active. Navigation validator passes cleanly per latest user-reported results (not independently executed by this agent). |
| **Backend Core Architecture** | Complete (`100%`) | FastAPI app factory, CORS configuration, Pydantic BaseSettings, `/api/v1/health` and `/api/v1/health/ready` endpoints active. Health route tests included in the user-reported 120-test suite (not independently executed by this agent). |
| **Database Domain Models** | Complete (`100%`) | 9 SQLAlchemy 2.0 ORM models (`users`, `institutions`, `bureaus`, `complaint_cases`, `case_assignments`, `case_events`, `case_relationships`, `coordination_actions`, `audit_logs`). Model/table registration tests included in the user-reported 120-test suite (not independently executed by this agent). |
| **Database Migrations** | Complete (`100%`) | Initial Alembic migration `2f4e9a1b8c72` committed and verified via offline Alembic CLI. |
| **Automated Testing Baseline** | Complete (100%) | Latest user-reported full backend pytest suite: 191 passed, 313 warnings in 2.53s. Focused lifecycle/event/complaint endpoint suite: 107 passed, 217 warnings in 2.10s. Navigation validation and `git diff --check` passed. Live PostgreSQL behavior remains unverified. |
| **Docker Compose PostgreSQL** | Configuration complete; live verification pending | PostgreSQL 16 container definition includes a persistent volume and health check. Runtime, live database connectivity, and migration execution have not been verified. |
| **Domain Services & REST APIs** | In Progress (~55%) | Institution CRUD and complaint CRUD routes are implemented. Complaint lifecycle management, status-transition validation, event staging, and the chronological case timeline are implemented and covered by passing automated tests. Institution normalized-name logic remains inline in the route; a dedicated complaint CRUD service layer, bureau assignment, relationship, and coordination APIs remain pending. |
| **AI Overlap Intelligence Engine** | Planned (`0%`) | Config parameters established (`AI_SIMILARITY_THRESHOLD`); vector/text matching service to be implemented. |
| **Frontend Dashboard & UI** | Planned (`0%`) | External integration designated for `frontend/` directory. |

---

## 3. Submission-Readiness Checklist

### 1. Repository Infrastructure & Navigation
- [x] Create root `AGENTS.md` primary entry point with operating protocol.
- [x] Create root `progress.md` progress tracker.
- [x] Create directory documentation for every source directory:
  - [x] `backend/backend.md`
  - [x] `backend/alembic/alembic.md`
  - [x] `backend/alembic/versions/versions.md`
  - [x] `backend/app/app.md`
  - [x] `backend/app/api/api.md`
  - [x] `backend/app/api/v1/v1.md`
  - [x] `backend/app/core/core.md`
  - [x] `backend/app/db/db.md`
  - [x] `backend/app/db/models/models.md`
  - [x] `backend/app/schemas/schemas.md`
  - [x] `backend/app/services/services.md`
  - [x] `backend/tests/tests.md`
  - [x] `scripts/scripts.md`
- [x] Create automated repository navigation validation script (`scripts/validate_navigation.py`).
- [x] Verify directory inventories and relative links.

### 2. Institution Management
- [x] ORM model for `institutions` table with partial unique index on `aicte_institution_id`.
- [x] Pydantic schemas: `InstitutionBase`, `InstitutionCreate`, `InstitutionRead`, `InstitutionSummary`, `InstitutionList`.
- [ ] Institution service layer with normalized name generation — normalized name computation is implemented inline in the API route (`_normalized_name` in `backend/app/api/v1/institutions.py`); `backend/app/services/` contains no service module.
- [x] REST API endpoints (`POST /api/v1/institutions`, `GET /api/v1/institutions`, `GET /api/v1/institutions/{id}`) — implemented in `backend/app/api/v1/institutions.py`, mounted in `backend/app/api/v1/router.py`. Duplicate AICTE ID returns HTTP 409.
- [x] Institution search, state/district filtering, and pagination — `list_institutions` supports case-insensitive `search` across `name`, `aicte_institution_id`, `state`, and `district`, with bounded `limit`/`offset`.
- [ ] Institution-specific complaint listing (`GET /api/v1/institutions/{id}/complaints`) — not implemented.

### 3. Complaint Registration & Tracking
- [x] ORM model for `complaint_cases` table with controlled `CaseStatus` and `CasePriority`.

- [x] Pydantic schemas: `ComplaintCaseBase`, `ComplaintCaseCreate`, `ComplaintCaseRead`, `ComplaintCaseUpdate`, `ComplaintCaseSummary`, `ComplaintCaseList`.

- [ ] Complaint CRUD service layer — a separate service abstraction for complaint CRUD remains pending. Lifecycle logic is implemented in `backend/app/services/case_lifecycle.py`.

- [x] REST API endpoints (`POST /api/v1/complaints`, `GET /api/v1/complaints`, `GET /api/v1/complaints/{id}`, `PATCH /api/v1/complaints/{id}`) — implemented in `backend/app/api/v1/complaints.py`, mounted in `backend/app/api/v1/router.py`. Duplicate `case_reference` returns HTTP 409; missing institution returns HTTP 404.

- [ ] Automatic case-reference generation — pending; case references are caller-supplied.

- [x] Caller-supplied case reference validation and uniqueness — `case_reference` is a unique caller-supplied field (e.g. `AICTE-PGRS-2026-001234`), enforced unique at the database level.

- [x] Timestamp and protected-field handling on PATCH — `PATCH` manages `closed_at` on transitions to and from terminal statuses (`closed`, `withdrawn`); protected fields (`id`, `case_reference`, `institution_id`, `received_at`, `closed_at`, timestamps) cannot be changed via `PATCH`.

- [x] Explicit status-transition rules and lifecycle state machine — implemented in `backend/app/services/case_lifecycle.py` and covered by passing automated tests. Invalid transitions return HTTP 422; same-status PATCH requests are idempotent.

- [x] Event logging and chronological case history — event staging for complaint creation and status/priority changes is implemented and covered by passing automated tests. `GET /api/v1/complaints/{case_id}/events` provides the chronological timeline.

### 4. Case Assignments & Transfers
- [x] ORM model for `case_assignments` table with partial unique index for single active assignment.
- [x] ORM model for `bureaus` table with uppercase code validation.
- [ ] Bureau assignment service supporting full transfer history without overwriting previous assignments.
- [ ] Transfer case endpoint (`POST /api/v1/complaints/{id}/transfer`).
- [ ] Bureau assignment history listing endpoint.

### 5. Case Lifecycle & Action History
- [x] ORM model for `case_events` with append-only design.
- [ ] Service hook to log automated events on status changes, assignments, and review actions.
- [ ] REST API endpoint for chronological case timeline (`GET /api/v1/complaints/{id}/events`).
- [ ] Evidence attachment and officer remark logging.

### 6. Cross-Bureau Overlap Detection & AI Matching
- [x] ORM model for `case_relationships` with canonical pair constraint (`source_case_id < target_case_id`).
- [x] Pydantic schemas for `CaseRelationshipCreate` rejecting self-links.
- [ ] AI matching service with configurable cosine similarity threshold (`AI_SIMILARITY_THRESHOLD`).
- [ ] Text embedding generation and category overlap scoring.
- [ ] Automatic detection pipeline triggered on complaint creation.

### 7. Human Review & Explainability
- [x] Database check constraints and schemas enforcing human-only confirmation of AI proposals.
- [ ] Review endpoints (`POST /api/v1/relationships/{id}/confirm`, `POST /api/v1/relationships/{id}/dismiss`).
- [ ] Explainability payload in API (matched terms, common institution, shared evidence).
- [ ] Prevention of autonomous case merges or automated status finalization.

### 8. Cross-Bureau Coordination Actions
- [x] ORM model for `coordination_actions` table linking primary and related cases.
- [ ] Action item creation and assignment to specific bureau officers.
- [ ] Status workflow (`pending`, `in_progress`, `completed`, `cancelled`).
- [ ] Cross-bureau coordination action queue endpoints.

### 9. Search, Filters, Sorting & Pagination
- [ ] Full-text search across complaint subject and description.
- [ ] Filter by bureau, institution, status, priority, and date range.
- [ ] Standardized paginated response schema.

### 10. Dashboard KPIs & Analytics
- [ ] Aggregated KPI endpoint (total cases, open cases, active transfers, flagged overlaps).
- [ ] Bureau-wise and region-wise breakdown analytics.
- [ ] Monthly filing trends and disposal rate metrics.

### 11. Pending-Case Ageing & Timeline Alerts
- [ ] Ageing calculation (days pending by priority).
- [ ] Overdue deadline warning triggers based on `due_at`.
- [ ] Escalation flag for critical cases exceeding target resolution windows.

### 12. Authentication & Role-Based Access Control (RBAC)
- [x] ORM model for `users` with `UserRole` enum (`officer`, `bureau_head`, `admin`, `analyst`).
- [ ] Password hashing, JWT token authentication, and auth dependencies.
- [ ] Role-based authorization on administrative and transfer endpoints.

### 13. Audit Logging & Security
- [x] ORM model for `audit_logs` table with JSON details and immutable record structure.
- [ ] Audit middleware or service decorator logging administrative actions.
- [ ] Sensitive complainant data protection and input sanitization.

### 14. Frontend / Backend Integration
- [x] CORS middleware configured and tested.
- [x] Standardized API error responses and OpenAPI schema generation.
- [ ] API client integration with frontend dashboard.

### 15. Database Integrity & Migrations
- [x] Initial Alembic migration establishing 9 core tables, foreign keys, and indexes.
- [x] PostgreSQL 16 Docker Compose environment configured.
- [ ] Migration execution verified against live PostgreSQL container.
- [ ] Database seed script for synthetic test data.

### 16. Automated Testing
- [x] Pytest suite configured with passing health probe and schema tests (7 passing).
- [ ] Database integration tests with isolated test session fixture.
- [ ] Service layer unit tests for AI matching and canonical relationship ordering.
- [ ] End-to-end API scenario tests.

### 17. Installation & Reproducibility
- [x] Pinned `requirements.txt` with clear Python version requirements.
- [x] `.env.example` with documented configuration parameters.
- [x] Docker Compose PostgreSQL setup with health checks.
- [ ] Single-command database setup and seed runner.

### 18. Synthetic Data & Demonstration Workflow
- [ ] Synthetic dataset containing realistic technical institutions (e.g. engineering, polytechnic).
- [ ] Scripted scenario demonstrating multi-bureau complaint submission (Regulation Bureau + PGRC).
- [ ] Automated overlap detection demonstration showing explainable similarity.
- [ ] Officer human review walk-through and joint coordination action resolution.

### 19. Deployment Configuration & Production Readiness
- [x] Production settings toggle (`APP_ENV=production` disables docs and adjusts logging).
- [ ] Dockerfile for containerized backend API service.
- [ ] Docker Compose full stack (API + PostgreSQL).

### 20. SIH Presentation & Materials
- [x] Problem statement alignment and architectural documentation in root README and AGENTS.md.
- [ ] Architecture diagrams and entity-relationship diagrams.
- [ ] Pitch deck alignment and 5-minute judge demonstration walk-through script.

---

## 4. Completed Deliverables (Verified with Evidence)

1. **Root Navigation & Agent Protocol:**
   - Files: `AGENTS.md`, `progress.md`.
   - Verified: Passes `python scripts/validate_navigation.py` (execution not re-verified after merge `6dd0d08`).
2. **Directory Documentation Coverage:**
   - 13 directories documented with standard sections (A through G).
   - Verified: 0 missing doc files, 0 broken relative links per latest user-reported results (not independently executed by this agent).
3. **Automated Navigation Validator:**
   - File: `scripts/validate_navigation.py`.
   - Verified: Executed successfully from repository root (`exit code 0`) per latest user-reported results (not independently executed by this agent).
4. **FastAPI Application Factory & Health Probes:**
   - Files: `backend/app/main.py`, `backend/app/api/v1/health.py`, `backend/app/api/v1/router.py`.
   - Verified: `GET /api/v1/health` returns 200 OK; `GET /api/v1/health/ready` returns 503 degraded when database is unconfigured (health route tests included in the user-reported 120-test suite; not independently executed by this agent).
5. **Relational Database Domain Models:**
   - Files: `backend/app/db/models/*.py`.
   - Verified: 9 tables registered on `Base.metadata` verified via `backend/tests/test_models.py` (model/table registration tests included in the user-reported 120-test suite; not independently executed by this agent).
6. **Alembic Initial Domain Migration:**
   - File: `backend/alembic/versions/20261020_2f4e9a1b8c72_initial_domain_schema.py`.
   - Verified: `alembic history --verbose` returns revision `2f4e9a1b8c72 (head)`.
7. **Pydantic Validation Schemas:**
   - Files: `backend/app/schemas/*.py`.
   - Verified: Whitespace stripping, non-null requirements, and timezone-aware datetime validation verified via Pytest (schema tests included in the user-reported 120-test suite; not independently executed by this agent).
8. **Institution CRUD API Routes:**
   - Files: `backend/app/api/v1/institutions.py`, `backend/app/schemas/institution.py`.
   - Verified: `POST /api/v1/institutions`, `GET /api/v1/institutions`, `GET /api/v1/institutions/{id}` implemented and mounted in `router.py`; duplicate AICTE ID returns HTTP 409 (endpoint tests exist at `backend/tests/test_institution_endpoints.py` and are covered by the user-reported 120-test suite; not independently executed by this agent).
9. **Complaint Case CRUD API Routes:**
   - Files: `backend/app/api/v1/complaints.py`, `backend/app/schemas/complaint_case.py`.
   - Verified: `POST /api/v1/complaints`, `GET /api/v1/complaints`, `GET /api/v1/complaints/{id}`, `PATCH /api/v1/complaints/{id}` implemented and mounted in `router.py`; duplicate `case_reference` returns HTTP 409; missing institution returns HTTP 404; `closed_at` managed on terminal status transitions (endpoint tests exist at `backend/tests/test_complaint_case_endpoints.py` and are covered by the user-reported 120-test suite; not independently executed by this agent).
10. **Automated Backend Test Suite:**
    - Directory: `backend/tests/`.
    - Verified: 120 backend tests passed per latest user-reported results (health routes, table registration, schema constraints, complaint-case endpoints); `scripts/validate_navigation.py` also passed per latest user-reported results. Not independently executed by this agent.

---

## 5. In-Progress Deliverables

- **Complaint Lifecycle & Event Timeline — implementation and automated verification complete**
  - Implemented status-transition validation, `closed_at` management, transactional event staging on complaint creation and status/priority changes, and the chronological timeline endpoint.
  - Added `CaseEventRead`, the `case_lifecycle.py` service, and lifecycle/event regression tests.
  - Focused tests: 107 passed, 217 warnings in 2.10s.
  - Full backend suite: 191 passed, 313 warnings in 2.53s.
  - Navigation validation and `git diff --check` passed.
  - Live PostgreSQL/Docker behavior remains unverified.

- **Remaining CRUD and service-layer work**
  - Institution CRUD and complaint CRUD routes are implemented.
  - Institution normalized-name generation remains inline in `institutions.py`.
  - A separate complaint CRUD service layer, bureau assignment/transfer APIs, relationship APIs, and coordination APIs remain to be implemented.

## 6. Remaining Deliverables

1. Implement the institution service layer with normalized name generation (institution CRUD routes exist; service abstraction remains pending).

2. Implement a dedicated complaint CRUD service layer (complaint CRUD routes and lifecycle service are implemented; a separate CRUD service remains pending).

3. Implement the institution-specific complaint listing endpoint (`GET /api/v1/institutions/{id}/complaints`).

4. Implement bureau management APIs and the case assignment/transfer service, preserving assignment history and recording relevant lifecycle events.

5. Implement case relationship APIs and the AI overlap detection engine with similarity scoring.

6. Implement the human review workflow for relationship confirmation and dismissal, including explainability information.

7. Implement cross-bureau coordination action queues and deadline escalation.

8. Implement complaint search, filtering, sorting, and pagination capabilities not yet available.

9. Implement dashboard analytics, KPI aggregation, and pending-case ageing calculations.

10. Implement JWT authentication and role-based permissions.

11. Create a synthetic demo data seeding script and reproducible demonstration scenarios.

12. Integrate the frontend dashboard with the backend APIs.

13. Prepare architecture diagrams, SIH presentation materials, and the judge demonstration walkthrough.

**Completed in the current module:** Complaint lifecycle transition rules, `closed_at` management, event staging for complaint creation and status/priority changes, and the chronological case timeline endpoint. Automated tests passed; live PostgreSQL/Docker verification remains pending.

---

## 7. Known Bugs and Technical Debt

1. **FastAPI Lifecycle Deprecation Warning:**
   - Notice: `app/main.py` uses `@app.on_event("startup")` and `@app.on_event("shutdown")`.
   - Impact: Emits deprecation warnings in FastAPI 0.115+.
   - Remediation: Refactor to modern `asynccontextmanager` lifespan handler during router expansion.
2. **Docker Runtime Availability:**
   - Docker Desktop is not currently running on the development host. Local tests run cleanly using mocks and unit validation, but end-to-end PostgreSQL tests require starting Docker Desktop.

---

## 8. Verification and Acceptance Criteria

| Deliverable | Acceptance Criteria | Test Command |
|---|---|---|
| Navigation System | 100% directory doc coverage, all child files listed, all links valid. | `python scripts/validate_navigation.py` |
| Health Probes | `/health` returns 200 with app metadata; `/health/ready` validates DB readiness. | `pytest tests/test_health.py -v` |
| Domain Models | All 9 tables defined with typed columns, constraints, and indexes. | `pytest tests/test_models.py -v` |
| Schema Validation | Pydantic models reject invalid data, naive datetimes, and self-relationships. | `pytest tests/test_models.py -v` |
| Migration Head | Alembic can inspect migration head revision cleanly without syntax errors. | `alembic history --verbose` |

---

## 9. Recent Progress Log

- **2026-10-20:**
  - Audited full repository structure and verified existing backend models, schemas, and migrations.
  - Created root `AGENTS.md` operating protocol and `progress.md` progress tracker.
  - Authored comprehensive directory documentation for all 13 project directories.
  - Implemented automated navigation validation tool `scripts/validate_navigation.py`.
  - Added the initial unit test suite in `backend/tests/` (7 passed — historical baseline).
  - Validated health probe endpoints and database model metadata completeness.

- **2026-10-21 (merge `6dd0d08` reconciliation):**
  - Verified Institution and Complaint Case CRUD API routes are implemented and mounted in `backend/app/api/v1/router.py`.
  - Confirmed normalized-name generation remains inline in the institution API route (`_normalized_name` in `institutions.py`); a dedicated institution service layer remains pending.
  - Reconciled project documentation with the implemented endpoints and remaining service-layer work.
  - Updated `backend/app/api/v1/v1.md` file inventory and directory tree to include `institutions.py` and `complaints.py`.

- **2026-10-21 (Complaint Lifecycle & Event Timeline):**
  - Implemented centralized complaint status-transition rules and `closed_at` lifecycle handling in `backend/app/services/case_lifecycle.py`.
  - Added transactional event staging for complaint creation and status/priority changes.
  - Added the `CaseEventRead` schema and `GET /api/v1/complaints/{case_id}/events` chronological timeline endpoint.
  - Added lifecycle and event tests, and updated complaint endpoint regression tests.
  - Fixed test helpers to capture staged events correctly and inspect compiled SQL bind parameters.
  - Focused lifecycle/event/complaint endpoint suite: **107 passed, 217 warnings in 2.10s**.
  - Full backend test suite: **191 passed, 313 warnings in 2.53s**.
  - Navigation validation passed for all 13 directories; `git diff --check` passed.
  - Live PostgreSQL/Docker verification remains pending.

---
## 10. Final Submission Checklist

- [ ] Complete end-to-end multi-bureau demonstration working smoothly.
- [ ] AI overlap engine produces explainable matches with confidence scores.
- [ ] Human review workflow properly updates case relationships.
- [ ] Interactive dashboard displays real-time analytics and ageing metrics.
- [ ] Docker Compose boots the full stack with single command.
- [ ] Database seeds with rich synthetic educational institution complaints.
- [ ] All automated unit and integration tests pass cleanly.
- [ ] Security and data privacy review completed.
- [ ] Presentation slide deck and demonstration script ready for SIH judges.
