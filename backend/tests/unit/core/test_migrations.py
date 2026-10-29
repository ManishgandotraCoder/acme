"""Migrations are the source of truth for the production schema; models must not drift."""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text

from app.core.database import Base, is_search_table, make_engine
from app.modules.employees import models  # noqa: F401  (register tables)

ALEMBIC_INI = Path(__file__).resolve().parents[3] / "alembic.ini"


def _alembic(url: str) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", url)
    return config


def test_migrated_schema_matches_the_models(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    command.upgrade(_alembic(url), "head")

    engine = make_engine(url)
    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection,
            opts={"include_object": lambda o, name, type_, *_: not is_search_table(name)},
        )
        drift = compare_metadata(context, Base.metadata)
    engine.dispose()

    assert drift == [], "Models changed without a migration: run `make migration m='...'`"


def test_downgrade_to_base_removes_all_tables(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    config = _alembic(url)
    command.upgrade(config, "head")
    command.downgrade(config, "base")

    engine = make_engine(url)
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    engine.dispose()


def test_migrated_database_has_a_working_search_index(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    command.upgrade(_alembic(url), "head")

    engine = make_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO employees (full_name, email, job_title, department, country, currency,"
                " annual_salary, annual_salary_usd, hire_date, created_at, updated_at) VALUES"
                " ('Priya Patel', 'priya@example.com', 'Engineer', 'Engineering', 'India', 'INR',"
                " 100, 1, '2020-01-01', '2020-01-01', '2020-01-01')"
            )
        )
        hits = connection.execute(
            text("SELECT rowid FROM employees_search WHERE employees_search MATCH '\"patel\"'")
        ).all()
    assert len(hits) == 1
    engine.dispose()
