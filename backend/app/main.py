from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.llm import LLMClient
from app.ai.ollama_client import OllamaClient
from app.api import ask, employees, insights
from app.api.errors import register_error_handlers
from app.config import Settings, get_settings
from app.db import create_schema, make_engine, make_session_factory


def create_app(settings: Settings | None = None, llm: LLMClient | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        create_schema(engine)
        http = None
        if llm is None:
            http = httpx.Client(
                base_url=settings.ollama_url, timeout=settings.ollama_timeout_seconds
            )
            app.state.llm = OllamaClient(http, model=settings.ollama_model)
        else:
            app.state.llm = llm
        app.state.session_factory = make_session_factory(engine)
        yield
        if http is not None:
            http.close()
        engine.dispose()

    app = FastAPI(title="ACME Salary Management", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    @app.get("/api/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    for module in (employees, insights, ask):
        app.include_router(module.router)
    return app
