from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.db.models.enums import CasePriority, CaseStatus
from app.schemas.complaint_case import (
    ComplaintCaseCreate,
    ComplaintCaseList,
    ComplaintCaseRead,
    ComplaintCaseUpdate,
)


def _valid_payload() -> dict:
    return {
        "institution_id": uuid4(),
        "case_reference": "AICTE-PGRS-2026-000001",
        "subject": "Delayed scholarship disbursement",
        "description": "Student reports repeated payment delays.",
        "category": "scholarship",
        "priority": CasePriority.HIGH,
        "received_at": datetime.now(timezone.utc),
        "due_at": datetime.now(timezone.utc) + timedelta(days=7),
    }


def test_complaint_case_valid_payload_succeeds() -> None:
    payload = ComplaintCaseCreate(**_valid_payload())

    assert payload.subject == "Delayed scholarship disbursement"
    assert payload.case_reference == "AICTE-PGRS-2026-000001"
    assert payload.priority == CasePriority.HIGH


def test_complaint_case_subject_and_reference_are_trimmed() -> None:
    data = _valid_payload()
    data["subject"] = "  Subject With Spaces  "
    data["case_reference"] = "  REF-001  "

    payload = ComplaintCaseCreate(**data)

    assert payload.subject == "Subject With Spaces"
    assert payload.case_reference == "REF-001"


@pytest.mark.parametrize("field_name", ["subject", "case_reference"])
@pytest.mark.parametrize("value", ["", "   ", "\n\t  "])
def test_complaint_case_empty_or_whitespace_subject_reference_rejected(
    field_name: str,
    value: str,
) -> None:
    data = _valid_payload()
    data[field_name] = value

    with pytest.raises(ValidationError):
        ComplaintCaseCreate(**data)


def test_complaint_case_received_at_must_be_timezone_aware() -> None:
    data = _valid_payload()
    data["received_at"] = datetime.utcnow()

    with pytest.raises(ValidationError):
        ComplaintCaseCreate(**data)


def test_complaint_case_due_at_must_be_timezone_aware_when_provided() -> None:
    data = _valid_payload()
    data["due_at"] = datetime.utcnow()

    with pytest.raises(ValidationError):
        ComplaintCaseCreate(**data)


def test_complaint_case_timezone_aware_datetimes_are_accepted() -> None:
    data = _valid_payload()
    aware_offset = timezone(timedelta(hours=5, minutes=30))
    data["received_at"] = datetime(2026, 10, 20, 10, 30, tzinfo=aware_offset)
    data["due_at"] = datetime(2026, 10, 27, 10, 30, tzinfo=aware_offset)

    payload = ComplaintCaseCreate(**data)

    assert payload.received_at.tzinfo is not None
    assert payload.due_at is not None
    assert payload.due_at.tzinfo is not None


def test_complaint_case_due_at_none_is_valid() -> None:
    data = _valid_payload()
    data["due_at"] = None

    payload = ComplaintCaseCreate(**data)

    assert payload.due_at is None


# --------------------------------------------------------------------------- #
# ComplaintCaseUpdate
# --------------------------------------------------------------------------- #

def _valid_update_payload() -> dict:
    return {
        "subject": "Updated subject",
        "description": "Updated description.",
        "category": "fee_refund",
        "priority": CasePriority.CRITICAL,
        "status": CaseStatus.UNDER_REVIEW,
        "due_at": datetime.now(timezone.utc),
    }


def test_complaint_case_update_partial_payload_keeps_only_provided_fields() -> None:
    """Omitted fields are absent from model_dump(exclude_unset=True)."""
    payload = ComplaintCaseUpdate(subject="  New subject  ")

    assert payload.subject == "New subject"
    dump = payload.model_dump(exclude_unset=True)
    assert dump == {"subject": "New subject"}


def test_complaint_case_update_explicit_null_differs_from_omitted() -> None:
    """An explicitly provided null is distinguished from an omitted field."""
    explicit_null = ComplaintCaseUpdate(due_at=None)
    assert explicit_null.model_dump(exclude_unset=True) == {"due_at": None}

    omitted = ComplaintCaseUpdate(subject="Updated subject")
    dump = omitted.model_dump(exclude_unset=True)
    assert dump == {"subject": "Updated subject"}
    assert "due_at" not in dump


def test_complaint_case_update_empty_payload_rejected() -> None:
    """An empty PATCH body must not validate."""
    with pytest.raises(ValidationError):
        ComplaintCaseUpdate()


def test_complaint_case_update_subject_is_trimmed() -> None:
    payload = ComplaintCaseUpdate(subject="  Trim me  ")
    assert payload.subject == "Trim me"


@pytest.mark.parametrize("value", ["", "   ", "\n\t  "])
def test_complaint_case_update_empty_subject_rejected(value: str) -> None:
    with pytest.raises(ValidationError):
        ComplaintCaseUpdate(subject=value)


def test_complaint_case_update_due_at_must_be_timezone_aware() -> None:
    data = _valid_update_payload()
    data["due_at"] = datetime.utcnow()
    with pytest.raises(ValidationError):
        ComplaintCaseUpdate(**data)


def test_complaint_case_update_due_at_none_clears_value() -> None:
    data = _valid_update_payload()
    data["due_at"] = None
    payload = ComplaintCaseUpdate(**data)
    assert payload.due_at is None


@pytest.mark.parametrize(
    "field_name,invalid_value",
    [
        ("status", "bogus"),
        ("priority", "bogus"),
    ],
)
def test_complaint_case_update_invalid_enum_rejected(
    field_name: str, invalid_value: str
) -> None:
    data = _valid_update_payload()
    data[field_name] = invalid_value
    with pytest.raises(ValidationError):
        ComplaintCaseUpdate(**data)


def test_complaint_case_update_subject_max_length_enforced() -> None:
    with pytest.raises(ValidationError):
        ComplaintCaseUpdate(subject="x" * 501)


@pytest.mark.parametrize(
    "protected_field",
    [
        "id",
        "case_reference",
        "institution_id",
        "received_at",
        "closed_at",
        "created_at",
        "updated_at",
    ],
)
def test_complaint_case_update_protected_fields_rejected(protected_field: str) -> None:
    """Unexpected fields, including server-controlled ones, are forbidden."""
    data = _valid_update_payload()
    data[protected_field] = "tampered"
    with pytest.raises(ValidationError):
        ComplaintCaseUpdate(**data)


# --------------------------------------------------------------------------- #
# ComplaintCaseList
# --------------------------------------------------------------------------- #

def _make_read_case() -> ComplaintCaseRead:
    return ComplaintCaseRead(
        id=uuid4(),
        case_reference="AICTE-PGRS-2026-000001",
        institution_id=uuid4(),
        institution=None,
        subject="Subject",
        description=None,
        category=None,
        priority=CasePriority.MEDIUM,
        status=CaseStatus.OPEN,
        received_at=datetime.now(timezone.utc),
        due_at=None,
        closed_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_complaint_case_list_valid_payload() -> None:
    case = _make_read_case()
    lst = ComplaintCaseList(items=[case], total=1, limit=20, offset=0)

    assert lst.total == 1
    assert lst.limit == 20
    assert lst.offset == 0
    assert len(lst.items) == 1
    assert lst.items[0].case_reference == "AICTE-PGRS-2026-000001"


def test_complaint_case_list_empty_page() -> None:
    lst = ComplaintCaseList(items=[], total=0, limit=20, offset=0)
    assert lst.total == 0
    assert lst.items == []


@pytest.mark.parametrize(
    "field_name,invalid_value",
    [
        ("total", -1),
        ("limit", 0),
        ("limit", -5),
        ("offset", -1),
    ],
)
def test_complaint_case_list_bounds_rejected(
    field_name: str, invalid_value: int
) -> None:
    data = {"items": [], "total": 0, "limit": 20, "offset": 0}
    data[field_name] = invalid_value
    with pytest.raises(ValidationError):
        ComplaintCaseList(**data)
