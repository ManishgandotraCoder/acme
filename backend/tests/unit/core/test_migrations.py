"""Migrations are the source of truth for the production schema; models must not drift."""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text

from app.core.database import Base, make_engine
from app.modules.employees import models  # noqa: F401  (register tables)
from tests.conftest import scratch_database

ALEMBIC_INI = Path(__file__).resolve().parents[3] / "alembic.ini"


def _alembic(url: str) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", url)
    return config


def test_migrated_schema_matches_the_models(postgres_url):
    with scratch_database(postgres_url) as url:
        command.upgrade(_alembic(url), "head")
        engine = make_engine(url)
        with engine.connect() as connection:
            drift = compare_metadata(MigrationContext.configure(connection), Base.metadata)
        engine.dispose()

    assert drift == [], "Models changed without a migration: run `make migration m='...'`"


def test_downgrade_to_base_removes_all_tables(postgres_url):
    with scratch_database(postgres_url) as url:
        config = _alembic(url)
        command.upgrade(config, "head")
        command.downgrade(config, "base")
        engine = make_engine(url)
        tables = set(inspect(engine).get_table_names())
        engine.dispose()

    assert tables == {"alembic_version"}


def test_migrated_database_supports_indexed_substring_search(postgres_url):
    with scratch_database(postgres_url) as url:
        command.upgrade(_alembic(url), "head")
        engine = make_engine(url)
        with engine.connect() as connection:
            trigram = connection.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")
            ).scalar()
            indexes = {i["name"] for i in inspect(connection).get_indexes("employees")}
        engine.dispose()

    assert trigram == 1
    assert {"ix_employees_full_name_trgm", "ix_employees_email_trgm"} <= indexes
