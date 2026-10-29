import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.errors import (
    BusinessRuleError,
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)

# Most specific first.
_STATUS_BY_CATEGORY: tuple[tuple[type[DomainError], int], ...] = (
    (NotFoundError, 404),
    (ConflictError, 409),
    (BusinessRuleError, 422),
    (PermissionDeniedError, 403),
    (ServiceUnavailableError, 503),
    (DomainError, 400),
)


def status_for(error: DomainError) -> int:
    return next(status for category, status in _STATUS_BY_CATEGORY if isinstance(error, category))


def register_error_handlers(app: FastAPI) -> None:
    async def handle_domain_error(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, DomainError)
        status = status_for(exc)
        if status >= 500:
            logger.warning("%s %s -> %s: %s", request.method, request.url.path, status, exc)
        return JSONResponse(status_code=status, content={"detail": exc.public_message})

    app.add_exception_handler(DomainError, handle_domain_error)
