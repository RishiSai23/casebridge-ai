"""
Institution API route handlers.

Endpoints
---------
POST /api/v1/institutions
    Create a new institution.  Returns HTTP 201 with the created institution.

GET /api/v1/institutions
    List institutions with bounded pagination.  An optional case-insensitive
    search matches against ``name``, ``aicte_institution_id``, ``state`` and
    ``district``.  Returns HTTP 200 with a paginated InstitutionList.

GET /api/v1/institutions/{institution_id}
    Retrieve a single institution by UUID.  Returns HTTP 404 when not found.

Database and error handling
---------------------------
* Uses the async ``get_db()`` session dependency from :mod:`app.db.session`.
  The route commits explicitly; the dependency never auto-commits.
* ``aicte_institution_id`` is unique among non-null values (partial unique
  index on the ``institutions`` table).  A violation is converted to HTTP 409
  instead of surfacing as HTTP 500.
* Raw database errors, connection details and stack traces are never returned
  to API clients.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.institution import Institution
from app.schemas.institution import (
    InstitutionCreate,
    InstitutionList,
    InstitutionRead,
)

router = APIRouter(prefix="/institutions", tags=["Institutions"])

# --------------------------------------------------------------------------- #
# Pagination
# --------------------------------------------------------------------------- #

DEFAULT_LIMIT = 20
MAX_LIMIT = 100

logger = logging.getLogger(__name__)


def _normalized_name(name: str) -> str:
    """Return the server-side normalised form of an institution name.

    Lowercases and collapses internal whitespace so lookups can be
    case-insensitive and whitespace-tolerant without a full-text index.
    """
    return " ".join(name.split()).lower()


@router.post(
    "",
    response_model=InstitutionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an institution",
    description=(
        "Register a new institution.  ``id``, ``normalized_name``, "
        "``created_at`` and ``updated_at`` are generated server-side and "
        "must not be supplied by the caller."
    ),
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "An institution with this AICTE ID already exists.",
        }
    },
)
async def create_institution(
    payload: InstitutionCreate,
    db: AsyncSession = Depends(get_db),
) -> InstitutionRead:
    """Create and persist a new Institution row."""
    institution = Institution(
        name=payload.name,
        normalized_name=_normalized_name(payload.name),
        aicte_institution_id=payload.aicte_institution_id,
        institution_type=payload.institution_type,
        state=payload.state,
        district=payload.district,
    )
    db.add(institution)
    try:
        await db.commit()
    except IntegrityError:
        # Partial unique index on aicte_institution_id is violated.
        # Roll back so the session can be reused, then report a clean 409.
        await db.rollback()
        logger.warning("Duplicate institution identifier rejected")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An institution with this AICTE ID already exists.",
        )
    await db.refresh(institution)
    return institution


@router.get(
    "",
    response_model=InstitutionList,
    summary="List institutions",
    description=(
        f"Return a paginated list of institutions.  Results are ordered by "
        f"name then ID so pagination is stable.  Use ``limit`` and "
        f"``offset`` to page; ``limit`` is capped at {MAX_LIMIT}."
    ),
)
async def list_institutions(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(
        DEFAULT_LIMIT,
        ge=1,
        le=MAX_LIMIT,
        description="Maximum number of institutions to return per page.",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of institutions to skip before the first result.",
    ),
    search: str | None = Query(
        None,
        description=(
            "Case-insensitive substring search across name, AICTE institution "
            "ID, state and district."
        ),
    ),
) -> InstitutionList:
    """Return a page of institutions, optionally filtered by search text."""
    filters: list = []
    if search:
        like = f"%{search}%"
        filters.append(
            or_(
                Institution.name.ilike(like),
                Institution.aicte_institution_id.ilike(like),
                Institution.state.ilike(like),
                Institution.district.ilike(like),
            )
        )

    count_stmt = select(func.count(Institution.id))
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = (await db.execute(count_stmt)).scalar()

    stmt = select(Institution)
    if filters:
        stmt = stmt.where(*filters)
    stmt = stmt.order_by(Institution.name.asc(), Institution.id.asc())
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return InstitutionList(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{institution_id}",
    response_model=InstitutionRead,
    summary="Retrieve an institution by ID",
    description="Returns HTTP 404 when no institution with the given UUID exists.",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Institution not found."},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "``institution_id`` is not a valid UUID."
        },
    },
)
async def get_institution(
    institution_id: UUID = Path(
        ..., description="UUID of the institution to retrieve."
    ),
    db: AsyncSession = Depends(get_db),
) -> InstitutionRead:
    """Return a single Institution by its primary key."""
    result = await db.execute(
        select(Institution).where(Institution.id == institution_id)
    )
    institution = result.scalars().first()
    if institution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found.",
        )
    return institution