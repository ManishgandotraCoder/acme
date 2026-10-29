import pytest
from pydantic import ValidationError

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
    url = "postgresql+psycopg://salary:salary@localhost:5433/salary"
    assert Settings(database_url=url).database_url == url


def test_without_configuration_the_app_uses_the_local_docker_database(monkeypatch):
    # Real connection strings carry passwords: they belong in .env or the host's secret store,
    # never in code that is committed.
    monkeypatch.delenv("SALARY_DATABASE_URL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://salary:salary@localhost:5433/salary"


def test_a_blank_model_provider_means_the_default():
    # Hosting dashboards may set an optional variable to "" rather than leaving it unset.
    assert Settings(llm_provider="").llm_provider == "ollama"


@pytest.mark.parametrize(
    "host",
    ["ep-old-leaf-...neon.tech", "db..example.com", "a" * 64 + ".example.com"],
)
def test_a_malformed_database_host_is_reported_by_name_without_the_password(host):
    # A shortened or mistyped host otherwise fails deep inside DNS with "label empty or too
    # long", and pydantic would echo the whole URL, password included, into the logs.
    with pytest.raises(ValidationError) as error:
        Settings(database_url=f"postgresql://user:s3cret@{host}/db")

    message = str(error.value)
    assert host in message
    assert "s3cret" not in message


def test_a_value_that_is_not_a_database_url_is_rejected_without_echoing_it():
    # e.g. Neon's "psql '<url>'" snippet pasted instead of the URL itself.
    with pytest.raises(ValidationError) as error:
        Settings(database_url="psql 'postgresql://user:s3cret@db.example.com/db'")

    message = str(error.value)
    assert "SALARY_DATABASE_URL" in message
    assert "s3cret" not in message
