"""Migrations are the source of truth for the production schema; models must not drift."""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.core.database import Base, make_engine
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
        drift = compare_metadata(MigrationContext.configure(connection), Base.metadata)
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
