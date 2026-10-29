from collections.abc import Iterator
from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.db import create_schema, make_engine, make_session_factory
from app.models import Employee


@pytest.fixture
def session() -> Iterator[Session]:
    engine = make_engine("sqlite://")
    create_schema(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s
    engine.dispose()


def build_employee(**overrides) -> Employee:
    """Test data builder with sensible defaults; override only what the test cares about."""
    defaults = dict(
        full_name="Ada Lovelace",
        email="ada@acme.test",
        job_title="Software Engineer",
        department="Engineering",
        country="United Kingdom",
        currency="GBP",
        annual_salary=80_000,
        hire_date=date(2020, 1, 15),
    )
    defaults.update(overrides)
    return Employee(**defaults)
