from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.db.models.enums import CasePriority
from app.schemas.complaint_case import ComplaintCaseCreate


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
