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
    Transitioning to ``closed``/``withdrawn`` sets ``closed_at``; transitioning
    from a terminal status to a non-terminal one clears it.

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
from app.db.models.complaint_case import ComplaintCase
from app.db.models.institution import Institution
from app.db.models.enums import CasePriority, CaseStatus
from app.schemas.complaint_case import (
    ComplaintCaseCreate,
    ComplaintCaseList,
    ComplaintCaseRead,
    ComplaintCaseUpdate,
)



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
    try:
        await db.commit()
    except IntegrityError:
        # Unique constraint on case_reference is violated.
        # Roll back so the session can be reused, then report a clean 409.
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

TERMINAL_STATUSES = {CaseStatus.CLOSED, CaseStatus.WITHDRAWN}

logger = logging.getLogger(__name__)


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
    """Partially update and persist an existing ComplaintCase row."""
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

    # Manage closed_at in domain logic based on status transitions.
    if "status" in update_data:
        new_status = update_data["status"]
        was_terminal = case.status in TERMINAL_STATUSES
        if new_status in TERMINAL_STATUSES and not was_terminal:
            case.closed_at = datetime.now(timezone.utc)
        elif new_status not in TERMINAL_STATUSES and was_terminal:
            case.closed_at = None
        # Otherwise preserve the existing closed_at.

    for field, value in update_data.items():
        setattr(case, field, value)

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