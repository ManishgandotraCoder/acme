"""Tests run against real PostgreSQL, the database production uses (ADR 0007).

One throwaway Postgres container per test session (or ``SALARY_TEST_DATABASE_URL`` if set,
e.g. in CI). The schema is created once; every test runs inside a transaction that is rolled
back, with ``session.commit()`` becoming a SAVEPOINT. Tests stay isolated and fast.
"""

import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date

import pytest
from sqlalchemy import Engine, make_url, text
from sqlalchemy.orm import Session

from app.core.database import Base, create_schema, make_engine
from app.modules.employees.models import Employee

POSTGRES_IMAGE = "postgres:17-alpine"


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    if url := os.environ.get("SALARY_TEST_DATABASE_URL"):
        yield url
        return
    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer(POSTGRES_IMAGE, driver="psycopg") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def engine(postgres_url: str) -> Iterator[Engine]:
    engine = make_engine(postgres_url)
    Base.metadata.drop_all(engine)  # a reused database may hold an old schema
    create_schema(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


@contextmanager
def scratch_database(postgres_url: str) -> Iterator[str]:
    """A brand-new empty database on the same server (for migration tests)."""
    admin = make_engine(postgres_url).execution_options(isolation_level="AUTOCOMMIT")
    name = f"scratch_{uuid.uuid4().hex[:12]}"
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        yield make_url(postgres_url).set(database=name).render_as_string(hide_password=False)
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


def build_employee(**overrides) -> Employee:
    """Test data builder with sensible defaults; override only what the test cares about."""
    defaults = dict(
        full_name="Ada Lovelace",
        email="ada@example.com",
        job_title="Software Engineer",
        department="Engineering",
        country="United Kingdom",
        currency="GBP",
        annual_salary=80_000,
        hire_date=date(2020, 1, 15),
    )
    defaults.update(overrides)
    return Employee(**defaults)
