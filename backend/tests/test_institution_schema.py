from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.institution import InstitutionCreate


def test_institution_create_valid_payload_succeeds() -> None:
    payload = InstitutionCreate(
        name="National Institute of Technology",
        aicte_institution_id="AICTE-1234",
        institution_type="college",
        state="Karnataka",
        district="Bengaluru Urban",
    )

    assert payload.name == "National Institute of Technology"
    assert payload.aicte_institution_id == "AICTE-1234"


def test_institution_name_is_trimmed() -> None:
    payload = InstitutionCreate(name="  Example Institute  ")

    assert payload.name == "Example Institute"


@pytest.mark.parametrize("raw_name", ["", "   ", "\t\n  "])
def test_institution_empty_or_whitespace_name_rejected(raw_name: str) -> None:
    with pytest.raises(ValidationError):
        InstitutionCreate(name=raw_name)


def test_institution_create_does_not_trust_client_normalized_name() -> None:
    payload = InstitutionCreate(
        name="Demo College",
        normalized_name="malicious-client-value",
    )

    dumped = payload.model_dump()
    assert "normalized_name" not in dumped
    assert not hasattr(payload, "normalized_name")
