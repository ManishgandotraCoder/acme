from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SALARY_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./salary.db"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
