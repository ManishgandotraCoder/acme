from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.database import create_schema, make_engine, make_session_factory
from app.core.dependencies import SessionDep
from app.core.http_errors import register_error_handlers
from app.core.logging import REQUEST_ID_HEADER, configure_logging, install_request_context
from app.modules.assistant.llm import LLMClient
from app.modules.assistant.ollama import OllamaClient
from app.modules.assistant.router import router as assistant_router
from app.modules.employees.router import router as employees_router
from app.modules.insights.router import router as insights_router


def create_app(settings: Settings | None = None, llm: LLMClient | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    engine = make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if settings.auto_create_schema:
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
        expose_headers=[REQUEST_ID_HEADER],
    )
    install_request_context(app)
    register_error_handlers(app)

    @app.get("/api/health", tags=["ops"])
    def health() -> dict[str, str]:
        """Liveness: the process is up."""
        return {"status": "ok"}

    @app.get("/api/ready", tags=["ops"])
    def ready(session: SessionDep) -> dict[str, str]:
        """Readiness: dependencies needed to serve traffic are reachable."""
        session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}

    for router in (employees_router, insights_router, assistant_router):
        app.include_router(router)
    if settings.static_dir:
        _serve_frontend(app, Path(settings.static_dir))
    return app


def _serve_frontend(app: FastAPI, dist: Path) -> None:
    """Serve the built SPA; unknown non-API paths return index.html for client routing."""
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(dist.resolve()):
            return FileResponse(candidate)
        return FileResponse(dist / "index.html")
