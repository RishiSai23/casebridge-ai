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
| **Repository Intelligence & Navigation** | Complete (`100%`) | All directories documented with Markdown files; `scripts/validate_navigation.py` passes all checks; root `AGENTS.md` and `progress.md` active. |
| **Backend Core Architecture** | Complete (`100%`) | FastAPI app factory, CORS configuration, Pydantic BaseSettings, `/api/v1/health` and `/api/v1/health/ready` endpoints active. |
| **Database Domain Models** | Complete (`100%`) | 9 SQLAlchemy 2.0 ORM models (`users`, `institutions`, `bureaus`, `complaint_cases`, `case_assignments`, `case_events`, `case_relationships`, `coordination_actions`, `audit_logs`). |
| **Database Migrations** | Complete (`100%`) | Initial Alembic migration `2f4e9a1b8c72` committed and verified via offline Alembic CLI. |
| **Automated Testing Baseline** | Complete (`100%`) | Pytest suite with 7 passing tests validating health routes, table registration, and schema constraints. |
| **Docker Compose PostgreSQL** | Ready (`100%`) | PostgreSQL 16 container definition configured with persistent volume and health check; runtime pending Docker Desktop availability. |
| **Domain Services & REST APIs** | In Progress (`25%`) | Pydantic schemas created for institutions, bureaus, cases, and relationships; CRUD endpoints and services to be implemented. |
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
- [x] Pydantic schemas: `InstitutionBase`, `InstitutionCreate`, `InstitutionRead`, `InstitutionSummary`.
- [ ] Institution service layer with normalized name generation.
- [ ] REST API endpoints (`POST /api/v1/institutions`, `GET /api/v1/institutions`, `GET /api/v1/institutions/{id}`).
- [ ] Institution search, state/district filtering, and case listing.

### 3. Complaint Registration & Tracking
- [x] ORM model for `complaint_cases` table with controlled `CaseStatus` and `CasePriority`.
- [x] Pydantic schemas: `ComplaintCaseBase`, `ComplaintCaseCreate`, `ComplaintCaseRead`, `ComplaintCaseSummary`.
- [ ] Complaint service layer with unique case ID generation.
- [ ] REST API endpoints (`POST /api/v1/complaints`, `GET /api/v1/complaints`, `GET /api/v1/complaints/{id}`).
- [ ] Status transition validation and lifecycle guardrails.

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
   - Verified: Passes `python scripts/validate_navigation.py`.
2. **Directory Documentation Coverage:**
   - 13 directories documented with standard sections (A through G).
   - Verified: 0 missing doc files, 0 broken relative links.
3. **Automated Navigation Validator:**
   - File: `scripts/validate_navigation.py`.
   - Verified: Executed successfully from repository root (`exit code 0`).
4. **FastAPI Application Factory & Health Probes:**
   - Files: `backend/app/main.py`, `backend/app/api/v1/health.py`, `backend/app/api/v1/router.py`.
   - Verified: `GET /api/v1/health` returns 200 OK; `GET /api/v1/health/ready` returns 503 degraded when database is unconfigured.
5. **Relational Database Domain Models:**
   - Files: `backend/app/db/models/*.py`.
   - Verified: 9 tables registered on `Base.metadata` verified via `backend/tests/test_models.py`.
6. **Alembic Initial Domain Migration:**
   - File: `backend/alembic/versions/20261020_2f4e9a1b8c72_initial_domain_schema.py`.
   - Verified: `alembic history --verbose` returns revision `2f4e9a1b8c72 (head)`.
7. **Pydantic Validation Schemas:**
   - Files: `backend/app/schemas/*.py`.
   - Verified: Whitespace stripping, non-null requirements, and timezone-aware datetime validation verified via Pytest.
8. **Automated Backend Test Suite:**
   - Directory: `backend/tests/`.
   - Verified: 7 passing unit tests executed via `pytest -v`.

---

## 5. In-Progress Deliverables

- **CRUD API Endpoints & Service Layer (Task 3):**
  - Building REST routes for institutions, complaint cases, bureau management, and case relationships.
  - Adding database transaction handling and service tests.

---

## 6. Remaining Deliverables

1. Implement institution CRUD service and API routes.
2. Implement complaint case filing, status lifecycle, and assignment service.
3. Implement AI overlap detection engine and similarity scoring.
4. Implement human review workflow for relationship confirmation and dismissal.
5. Implement cross-bureau coordination action queues and deadline escalation.
6. Implement dashboard analytics, ageing calculations, and search endpoints.
7. Implement JWT authentication and role-based permissions.
8. Create synthetic demo data seeding script.
9. Integrate frontend dashboard application.
10. Finalize SIH presentation walk-through materials.

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
  - Added unit test suite in `backend/tests/` (7 passed).
  - Validated health probe endpoints and database model metadata completeness.

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
