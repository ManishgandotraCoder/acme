from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Hosting providers (Render, Heroku, ...) hand out driver-less URLs; SQLAlchemy would then pick
# psycopg2, which isn't installed.
_DRIVERLESS_SCHEMES = ("postgres://", "postgresql://")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SALARY_", env_file=".env", extra="ignore", populate_by_name=True
    )

    # Local docker-compose Postgres. Any real database URL carries a password: set it in
    # backend/.env or the host's secret store (SALARY_DATABASE_URL), never here.
    database_url: str = "postgresql+psycopg://salary:salary@localhost:5433/salary"
    # Production schema is managed by Alembic (`alembic upgrade head`). Tests opt in to a
    # fast create_all() instead.
    auto_create_schema: bool = False
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]
    # Language models that classify questions (app/modules/assistant/providers.py). Ollama is
    # always offered; Claude and OpenAI only when their API key is set (either name works).
    llm_provider: str = "ollama"  # the default: ollama | anthropic | openai
    llm_timeout_seconds: float = 30.0
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    anthropic_api_key: str | None = Field(
        default=None, validation_alias=AliasChoices("SALARY_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY")
    )
    anthropic_model: str = "claude-opus-5-5"
    openai_api_key: str | None = Field(
        default=None, validation_alias=AliasChoices("SALARY_OPENAI_API_KEY", "OPENAI_API_KEY")
    )
    openai_model: str = "gpt-4.1-mini"
    # Directory of the built frontend (frontend/dist). When set, the API also serves the UI.
    static_dir: str | None = None
    # Who the app acts as until SSO exists (see app/core/actor.py).
    actor_name: str = "HR Manager"
    actor_permissions: list[str] = ["view_individual_pay"]

    @field_validator("llm_provider")
    @classmethod
    def _blank_means_default(cls, provider: str) -> str:
        return provider.strip() or "ollama"

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, url: str) -> str:
        for scheme in _DRIVERLESS_SCHEMES:
            if url.startswith(scheme):
                return "postgresql+psycopg://" + url.removeprefix(scheme)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
