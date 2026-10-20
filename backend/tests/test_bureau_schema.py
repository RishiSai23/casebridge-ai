from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.bureau import BureauCreate


def test_bureau_valid_code_normalized_to_uppercase() -> None:
    payload = BureauCreate(code="legal", name="Legal Cell")

    assert payload.code == "LEGAL"
    assert payload.name == "Legal Cell"


def test_bureau_code_and_name_whitespace_handling() -> None:
    payload = BureauCreate(code="  pgrs  ", name="  Public Grievance Cell  ")

    assert payload.code == "PGRS"
    assert payload.name == "Public Grievance Cell"


@pytest.mark.parametrize("raw_code", ["", "   ", "\t\n  "])
def test_bureau_empty_or_whitespace_code_rejected(raw_code: str) -> None:
    with pytest.raises(ValidationError):
        BureauCreate(code=raw_code, name="Some Bureau")


@pytest.mark.parametrize("raw_name", ["", "   ", "\t\n  "])
def test_bureau_empty_or_whitespace_name_rejected(raw_name: str) -> None:
    with pytest.raises(ValidationError):
        BureauCreate(code="LEGAL", name=raw_name)
