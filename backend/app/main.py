"""Composition root: wires settings, infrastructure and modules into a FastAPI app."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import ops
from app.core.actor import Actor
from app.core.config import Settings, get_settings
from app.core.database import create_schema, make_engine, make_session_factory
from app.core.frontend import serve_frontend
from app.core.http_errors import register_error_handlers
from app.core.logging import REQUEST_ID_HEADER, configure_logging, install_request_context
from app.modules.assistant.providers import ProviderRegistry, build_registry
from app.modules.assistant.router import router as assistant_router
from app.modules.employees import models as _employee_models  # noqa: F401  (register tables)
from app.modules.employees.router import router as employees_router
from app.modules.insights.router import router as insights_router

ROUTERS = (ops.router, employees_router, insights_router, assistant_router)


def create_app(
    settings: Settings | None = None, providers: ProviderRegistry | None = None
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    engine = make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if settings.auto_create_schema:
            create_schema(engine)
        app.state.session_factory = make_session_factory(engine)
        app.state.actor = Actor(settings.actor_name, frozenset(settings.actor_permissions))
        app.state.llm_providers = providers or build_registry(settings)
        yield
        if providers is None:
            app.state.llm_providers.close()
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

    for router in ROUTERS:
        app.include_router(router)
    if settings.static_dir:
        serve_frontend(app, Path(settings.static_dir))
    return app
