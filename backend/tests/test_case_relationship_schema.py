from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.db.models.enums import RelationshipType
from app.schemas.case_relationship import CaseRelationshipCreate


def test_case_relationship_valid_payload_succeeds() -> None:
    payload = CaseRelationshipCreate(
        case_a_id=uuid4(),
        case_b_id=uuid4(),
        relationship_type=RelationshipType.SIMILAR_SUBJECT,
    )

    assert payload.relationship_type == RelationshipType.SIMILAR_SUBJECT


def test_case_relationship_self_relationship_rejected() -> None:
    same_id = uuid4()

    with pytest.raises(ValidationError):
        CaseRelationshipCreate(
            case_a_id=same_id,
            case_b_id=same_id,
            relationship_type=RelationshipType.SAME_INSTITUTION,
        )


def test_case_relationship_extra_fields_rejected_when_forbidden() -> None:
    with pytest.raises(ValidationError):
        CaseRelationshipCreate(
            case_a_id=uuid4(),
            case_b_id=uuid4(),
            relationship_type=RelationshipType.REPEATED_COMPLAINT,
            confidence_score=0.92,
        )
