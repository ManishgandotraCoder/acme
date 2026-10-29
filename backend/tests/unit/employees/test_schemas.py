from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.modules.employees.schemas import EmployeeCreate, EmployeeUpdate

VALID = dict(
    full_name="  Ada Lovelace  ",
    email="ada@example.com",
    job_title="Software Engineer",
    department="Engineering",
    country="United Kingdom",
    annual_salary=80_000,
    hire_date=date(2020, 1, 15),
)


def test_valid_payload_is_accepted_and_whitespace_trimmed():
    assert EmployeeCreate(**VALID).full_name == "Ada Lovelace"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("country", "Atlantis"),
        ("annual_salary", 0),
        ("annual_salary", -5),
        ("email", "not-an-email"),
        ("full_name", "   "),
        ("hire_date", date.today() + timedelta(days=1)),
    ],
)
def test_invalid_fields_are_rejected(field, value):
    with pytest.raises(ValidationError) as exc:
        EmployeeCreate(**{**VALID, field: value})
    assert exc.value.errors()[0]["loc"] == (field,)


def test_update_allows_partial_payload_but_still_validates():
    assert EmployeeUpdate(annual_salary=90_000).model_dump(exclude_unset=True) == {
        "annual_salary": 90_000
    }
    with pytest.raises(ValidationError):
        EmployeeUpdate(country="Atlantis")
