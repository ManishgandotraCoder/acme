"""Logging setup and per-request context (request id, access log)."""

import logging
import re
import time
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, Request, Response

REQUEST_ID_HEADER = "X-Request-ID"
_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")  # never echo arbitrary client input into logs

access_logger = logging.getLogger("app.request")


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = getattr(record, "request_id", _request_id.get())
        return True


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.addFilter(_RequestIdFilter())
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s")
    )
    root = logging.getLogger("app")
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    root.propagate = True  # still visible to pytest's caplog


def install_request_context(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(request: Request, call_next) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if _SAFE_ID.match(incoming) else uuid.uuid4().hex
        token = _request_id.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            _request_id.reset(token)
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        response.headers[REQUEST_ID_HEADER] = request_id
        access_logger.info(
            "%s %s -> %s in %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
