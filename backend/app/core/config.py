from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Hosting providers (Render, Heroku, ...) hand out driver-less URLs; SQLAlchemy would then pick
# psycopg2, which isn't installed.
_DRIVERLESS_SCHEMES = ("postgres://", "postgresql://")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SALARY_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://salary:salary@localhost:5433/salary"
    # Production schema is managed by Alembic (`alembic upgrade head`). Tests opt in to a
    # fast create_all() instead.
    auto_create_schema: bool = False
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: float = 30.0
    # Directory of the built frontend (frontend/dist). When set, the API also serves the UI.
    static_dir: str | None = None

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
