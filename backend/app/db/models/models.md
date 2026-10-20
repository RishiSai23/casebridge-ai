# Database Models Directory (`backend/app/db/models/`)

## A. Purpose
The `backend/app/db/models/` directory defines the SQLAlchemy 2.x declarative ORM models and domain enumerations representing the entire CaseBridge AI relational data domain.

## B. Directory tree
```
backend/app/db/models/
├── __init__.py                # Package exports and metadata registration for Alembic
├── audit_log.py               # Immutable audit log model
├── base.py                    # Base declarative class and TimestampMixin
├── bureau.py                  # AICTE Bureau / Cell model
├── case_assignment.py         # Bureau case ownership and assignment transfer model
├── case_event.py              # Chronological append-only case event timeline model
├── case_relationship.py       # Cross-bureau related-case and overlap mapping model
├── complaint_case.py          # Complaint filing model with status and priority
├── coordination_action.py     # Cross-bureau coordination action item model
├── enums.py                   # Controlled domain enumerations (CaseStatus, Priority, etc.)
├── institution.py             # Educational institution master profile model
├── models.md                  # Navigation documentation for db models
└── user.py                    # Platform staff user model
```

## C. File inventory
| File | Responsibility |
|---|---|
| `__init__.py` | Aggregates all model imports into `Base.metadata` to ensure complete schema discovery by Alembic and exports `__all__`. |
| `audit_log.py` | Defines `AuditLog` for immutable records of administrative and regulatory actions. |
| `base.py` | Defines SQLAlchemy 2.0 `Base` class and `TimestampMixin` providing server-generated UTC timestamps. |
| `bureau.py` | Defines `Bureau` representing AICTE bureaus/cells (e.g., PGRC, Regulation Bureau). |
| `case_assignment.py` | Defines `CaseAssignment` tracking active ownership and historical bureau case transfers. |
| `case_event.py` | Defines `CaseEvent` for append-only tamper-evident case activity timelines. |
| `case_relationship.py` | Defines `CaseRelationship` for AI-detected overlap and human-reviewed case links with canonical pair ordering. |
| `complaint_case.py` | Defines `ComplaintCase` for registered grievances and regulatory complaints. |
| `coordination_action.py` | Defines `CoordinationAction` for joint tasks, deadlines, and inter-bureau action items. |
| `enums.py` | Centralizes domain string enumerations (`CaseStatus`, `CasePriority`, `AssignmentStatus`, `RelationshipType`, `RelationshipStatus`, etc.). |
| `institution.py` | Defines `Institution` representing educational institutions with external AICTE IDs and normalized names. |
| `models.md` | Documents the domain models, invariants, relational constraints, and table mappings. |
| `user.py` | Defines `User` representing platform staff, bureau officers, analysts, and administrators. |

## D. Subdirectory inventory
There are currently no subdirectories in `backend/app/db/models/`.

## E. Relationships and dependencies
- All models inherit `Base` and `TimestampMixin` from [base.py](base.py).
- Uses string enums from [enums.py](enums.py) for all status and type columns.
- Exposed to Alembic via [app/db/models/__init__.py](__init__.py) and used by migrations in [backend/alembic/versions/](../../../alembic/versions/versions.md).
- Paired with Pydantic validation schemas in [backend/app/schemas/](../../schemas/schemas.md).

## F. Development and verification
Verified by automated model and metadata integrity tests in [backend/tests/test_models.py](../../../tests/test_models.py):
```powershell
pytest tests/test_models.py -v
```

## G. Maintenance notes
- Enforce canonical ordering on relationships: `source_case_id < target_case_id` to prevent duplicate reciprocal rows.
- Partial unique indexes are enforced on `institutions.aicte_institution_id` (non-null unique) and `case_assignments` (one active assignment per case).
- All new models must be imported in `__init__.py` to maintain Alembic discovery.
- Use `RESTRICT` on delete for critical relational data (institutions, cases, events) to preserve regulatory audit trails.
