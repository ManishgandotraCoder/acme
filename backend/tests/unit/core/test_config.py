import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    "given",
    [
        "postgres://user:secret@db.example.com:5432/salary",
        "postgresql://user:secret@db.example.com:5432/salary",
    ],
)
def test_plain_postgres_urls_from_hosting_providers_use_the_psycopg_driver(given):
    # Render, Heroku and others hand out driver-less URLs; SQLAlchemy would pick psycopg2,
    # which isn't installed.
    settings = Settings(database_url=given)

    assert settings.database_url == "postgresql+psycopg://user:secret@db.example.com:5432/salary"


def test_urls_that_already_name_a_driver_are_left_alone():
    url = "postgresql://neondb_owner:npg_uMkfs2c8Wrvy@ep-old-leaf-b5xvlmoe-pooler.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    assert Settings(database_url=url).database_url == url


def test_a_blank_model_provider_means_the_default():
    # Hosting dashboards may set an optional variable to "" rather than leaving it unset.
    assert Settings(llm_provider="").llm_provider == "ollama"
