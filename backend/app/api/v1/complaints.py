"""
Complaint Case API route handlers.

Endpoints
---------
POST /api/v1/complaints
    Create a new complaint case.  Status is always initialised to ``open`` and
    ``closed_at`` to ``None`` server-side.  Returns HTTP 201 with the created
    case.  A duplicate ``case_reference`` yields HTTP 409.

GET /api/v1/complaints
    List complaint cases with bounded pagination and optional status, priority,
    institution_id and category filters.  Returns HTTP 200 with a paginated
    ComplaintCaseList.  Filtering, counting and ordering are pushed to the
    database.

GET /api/v1/complaints/{case_id}
    Retrieve a single complaint case by UUID.  Returns HTTP 404 when not found.

PATCH /api/v1/complaints/{case_id}
    Partially update a complaint case.  Only explicitly provided fields are
    mutated.  ``case_reference``, ``institution_id``, ``received_at``,
    ``closed_at`` and timestamps cannot be changed through this endpoint.
    Status changes are validated by
    :mod:`app.services.case_lifecycle` (invalid transitions → HTTP 422).
    Transitioning to ``closed``/``withdrawn`` sets ``closed_at``; transitioning
    from a terminal status to a non-terminal one clears it.  Accepted status
    and priority changes append ``CaseEvent`` rows in the same transaction.

GET /api/v1/complaints/{case_id}/events
    Chronological, append-only case timeline (oldest first; ``id`` tie-breaker).

Database and error handling
---------------------------
* Uses the async ``get_db()`` session dependency from :mod:`app.db.session`.
  The route commits explicitly; the dependency never auto-commits.
* A missing referenced institution is reported as HTTP 404, matching the
  Institution API's resource-not-found convention, rather than as a database
  outage.
* ``case_reference`` is unique; an integrity conflict is converted to HTTP 409
  after a rollback instead of surfacing as HTTP 500.
* Raw database errors, connection details and stack traces are never returned
  to API clients.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.case_event import CaseEvent
from app.db.models.complaint_case import ComplaintCase
from app.db.models.institution import Institution
from app.db.models.enums import CaseEventType, CasePriority, CaseStatus
from app.schemas.case_event import CaseEventRead
from app.schemas.complaint_case import (
    ComplaintCaseCreate,
    ComplaintCaseList,
    ComplaintCaseRead,
    ComplaintCaseUpdate,
)
from app.services.case_lifecycle import (
    manage_closed_at,
    record_case_event,
    validate_status_transition,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/complaints", tags=["Complaints"])


@router.post(
    "",
    response_model=ComplaintCaseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a complaint case",
    description=(
        "Register a new complaint case.  ``id``, ``status`` (always ``open``), "
        "``closed_at`` and timestamps are generated server-side and must not be "
        "supplied by the caller."
    ),
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "A complaint case with this reference already exists.",
        }
    },
)
async def create_complaint_case(
    payload: ComplaintCaseCreate,
    db: AsyncSession = Depends(get_db),
) -> ComplaintCaseRead:
    """Create and persist a new ComplaintCase row."""

    # Validate the referenced institution before touching complaint state so a
    # missing institution is reported as a client error (HTTP 404), never as a
    # database outage.
    institution_result = await db.execute(
        select(Institution).where(Institution.id == payload.institution_id)
    )
    if institution_result.scalars().first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found.",
        )

    case = ComplaintCase(
        case_reference=payload.case_reference,
        institution_id=payload.institution_id,
        subject=payload.subject,
        description=payload.description,
        category=payload.category,
        priority=payload.priority,
        status=CaseStatus.OPEN,
        received_at=payload.received_at,
        due_at=payload.due_at,
        closed_at=None,
    )
    db.add(case)

    # Record the initial creation event in the same transaction so that a
    # failed commit rolls both the case and the event back together.
    record_case_event(
        db,
        case,
        CaseEventType.CREATED,
        "Complaint case created.",
    )

    try:
        await db.commit()
    except IntegrityError:
        # Unique constraint on case_reference is violated.
        # Roll back so the session can be reused, then report a clean 409.
        # The CREATED event is rolled back along with the case row.
        await db.rollback()
        logger.warning("Duplicate complaint case reference rejected")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A complaint case with this reference already exists.",
        )
    await db.refresh(case)
    return case


# --------------------------------------------------------------------------- #
# Pagination
# --------------------------------------------------------------------------- #

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


@router.get(
    "",
    response_model=ComplaintCaseList,
    summary="List complaint cases",
    description=(
        "Return a paginated list of complaint cases.  Results are ordered by "
        "created_at descending with ID as a stable tie-breaker so pagination is "
        "stable.  Use ``limit`` and ``offset`` to page; ``limit`` is capped at "
        f"{MAX_LIMIT}.  Optional ``status``, ``priority``, ``institution_id`` "
        "and ``category`` filters are applied to both the count and the data "
        "query."
    ),
)
async def list_complaint_cases(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(
        DEFAULT_LIMIT,
        ge=1,
        le=MAX_LIMIT,
        description="Maximum number of complaint cases to return per page.",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of complaint cases to skip before the first result.",
    ),
    status: CaseStatus | None = Query(
        None,
        description="Filter by complaint case lifecycle status.",
    ),
    priority: CasePriority | None = Query(
        None,
        description="Filter by complaint case priority.",
    ),
    institution_id: UUID | None = Query(
        None,
        description="Filter by the institution the case concerns.",
    ),
    category: str | None = Query(
        None,
        description="Filter by complaint case category.",
    ),
) -> ComplaintCaseList:
    """Return a page of complaint cases, optionally filtered."""

    filters: list = []
    if status is not None:
        filters.append(ComplaintCase.status == status)
    if priority is not None:
        filters.append(ComplaintCase.priority == priority)
    if institution_id is not None:
        filters.append(ComplaintCase.institution_id == institution_id)
    if category is not None:
        filters.append(ComplaintCase.category == category)

    count_stmt = select(func.count(ComplaintCase.id))
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = (await db.execute(count_stmt)).scalar()

    stmt = select(ComplaintCase)
    if filters:
        stmt = stmt.where(*filters)
    stmt = stmt.order_by(ComplaintCase.created_at.desc(), ComplaintCase.id.asc())
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return ComplaintCaseList(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{case_id}",
    response_model=ComplaintCaseRead,
    summary="Retrieve a complaint case by ID",
    description="Returns HTTP 404 when no complaint case with the given UUID exists.",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Complaint case not found."},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "``case_id`` is not a valid UUID."
        },
    },
)
async def get_complaint_case(
    case_id: UUID = Path(..., description="UUID of the complaint case to retrieve."),
    db: AsyncSession = Depends(get_db),
) -> ComplaintCaseRead:
    """Return a single ComplaintCase by its primary key."""
    result = await db.execute(
        select(ComplaintCase).where(ComplaintCase.id == case_id)
    )
    case = result.scalars().first()
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint case not found.",
        )
    return case


@router.patch(
    "/{case_id}",
    response_model=ComplaintCaseRead,
    summary="Partially update a complaint case",
    description=(
        "Update only the fields explicitly supplied in the request body.  "
        "``id``, ``case_reference``, ``institution_id``, ``received_at``, "
        "``closed_at`` and timestamps cannot be changed here.  When the status "
        "transitions to ``closed`` or ``withdrawn``, ``closed_at`` is set to "
        "the current UTC time; when it moves from a terminal status to a "
        "non-terminal one, ``closed_at`` is cleared."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Complaint case not found."},
        status.HTTP_409_CONFLICT: {
            "description": "A complaint case with this reference already exists."
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Validation error: empty payload, invalid field, or "
            "attempt to change a protected field."
        },
    },
)
async def update_complaint_case(
    case_id: UUID = Path(..., description="UUID of the complaint case to update."),
    payload: ComplaintCaseUpdate = ...,
    db: AsyncSession = Depends(get_db),
) -> ComplaintCaseRead:
    """Partially update and persist an existing ComplaintCase row.

    Status transitions are validated centrally via
    :func:`app.services.case_lifecycle.validate_status_transition`; invalid
    transitions are rejected with HTTP 422.  All accepted mutations and any
    corresponding case events are committed atomically — a failure rolls
    both back.
    """
    result = await db.execute(
        select(ComplaintCase).where(ComplaintCase.id == case_id)
    )
    case = result.scalars().first()
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint case not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    # The schema validator rejects an empty payload, so update_data is
    # guaranteed non-empty here.

    # Capture pre-mutation values for event recording and transition checks.
    old_status = case.status
    old_priority = case.priority
    new_status = update_data.get("status")

    # Validate the status transition before mutating anything.
    if new_status is not None and new_status != old_status:
        try:
            validate_status_transition(old_status, new_status)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            )

    # Manage closed_at based on terminal-status transitions.
    manage_closed_at(case, new_status)

    # Apply all field updates (status included if present).
    for field, value in update_data.items():
        setattr(case, field, value)

    # Record lifecycle events for meaningful changes, before commit so the
    # event and the case mutation share the same transaction.
    if new_status is not None and new_status != old_status:
        record_case_event(
            db,
            case,
            CaseEventType.STATUS_CHANGED,
            f"Status changed from '{old_status.value}' to '{new_status.value}'.",
            event_metadata={
                "old_status": old_status.value,
                "new_status": new_status.value,
            },
        )
    if "priority" in update_data and update_data["priority"] != old_priority:
        record_case_event(
            db,
            case,
            CaseEventType.PRIORITY_CHANGED,
            f"Priority changed from '{old_priority.value}' to '{case.priority.value}'.",
            event_metadata={
                "old_priority": old_priority.value,
                "new_priority": case.priority.value,
            },
        )

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        logger.warning("Complaint case update rejected due to integrity conflict")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A complaint case with this reference already exists.",
        )
    await db.refresh(case)
    return case


@router.get(
    "/{case_id}/events",
    response_model=list[CaseEventRead],
    summary="List case events in chronological order",
    description=(
        "Return all events for a complaint case, ordered chronologically "
        "by ``occurred_at`` with ``id`` as a stable tie-breaker when "
        "timestamps match.  Returns an empty collection when the case "
        "exists but has no events."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Complaint case not found."},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "``case_id`` is not a valid UUID."
        },
    },
)
async def list_case_events(
    case_id: UUID = Path(..., description="UUID of the complaint case."),
    db: AsyncSession = Depends(get_db),
) -> list[CaseEventRead]:
    """Return all events for a case, oldest first.

    Validates that the case exists (HTTP 404 otherwise) and returns only
    events belonging to that case.  No relationship loading is performed,
    avoiding N+1 queries.
    """
    # Validate the case exists before returning its events.
    result = await db.execute(
        select(ComplaintCase).where(ComplaintCase.id == case_id)
    )
    if result.scalars().first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint case not found.",
        )

    # Fetch events for this case only, chronologically ordered.
    # Secondary sort by id guarantees deterministic ordering when
    # occurred_at values are identical.
    result = await db.execute(
        select(CaseEvent)
        .where(CaseEvent.case_id == case_id)
        .order_by(CaseEvent.occurred_at.asc(), CaseEvent.id.asc())
    )
    events = result.scalars().all()
    return list(events)