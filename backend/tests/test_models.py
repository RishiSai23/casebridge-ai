"""
Unit tests for domain models, metadata, and schema validation.
"""

from uuid import uuid4
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from app.db.models.base import Base
import app.db.models  # noqa: F401
from app.db.models.enums import CasePriority, CaseStatus, RelationshipType
from app.schemas.institution import InstitutionCreate
from app.schemas.case_relationship import CaseRelationshipCreate
from app.schemas.complaint_case import ComplaintCaseBase


def test_models_metadata_completeness() -> None:
    """Verify that all core tables are registered on Base.metadata."""
    expected_tables = {
        "users",
        "institutions",
        "bureaus",
        "complaint_cases",
        "case_assignments",
        "case_events",
        "case_relationships",
        "coordination_actions",
        "audit_logs",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"


def test_institution_create_schema_validation() -> None:
    """Test InstitutionCreate trims whitespace and rejects empty string."""
    inst = InstitutionCreate(name="  AICTE Institute of Technology  ", state="Delhi")
    assert inst.name == "AICTE Institute of Technology"

    with pytest.raises(ValidationError):
        InstitutionCreate(name="   ")


def test_case_relationship_create_self_relation_rejected() -> None:
    """Test CaseRelationshipCreate forbids relating a case to itself."""
    case_id = uuid4()
    with pytest.raises(ValidationError):
        CaseRelationshipCreate(
            case_a_id=case_id,
            case_b_id=case_id,
            relationship_type=RelationshipType.SAME_INSTITUTION,
        )


def test_case_relationship_create_valid() -> None:
    """Test CaseRelationshipCreate succeeds with distinct cases."""
    case_a = uuid4()
    case_b = uuid4()
    rel = CaseRelationshipCreate(
        case_a_id=case_a,
        case_b_id=case_b,
        relationship_type=RelationshipType.SIMILAR_SUBJECT,
    )
    assert rel.case_a_id == case_a
    assert rel.case_b_id == case_b


def test_complaint_case_requires_timezone_aware_datetime() -> None:
    """Test ComplaintCaseBase requires timezone-aware datetime."""
    # Timezone-naive datetime should raise ValidationError
    naive_dt = datetime(2026, 10, 20, 12, 0, 0)
    with pytest.raises(ValidationError):
        ComplaintCaseBase(
            subject="Test complaint",
            received_at=naive_dt,
        )

    # Timezone-aware datetime should pass
    aware_dt = datetime.now(timezone.utc)
    case = ComplaintCaseBase(
        subject="Valid complaint",
        received_at=aware_dt,
    )
    assert case.subject == "Valid complaint"
    assert case.priority == CasePriority.MEDIUM
