from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.modules.assistant.llm import LLMUnavailableError
from app.modules.employees.service import (
    CurrencyChangeRequiresSalaryError,
    DuplicateEmailError,
    EmployeeNotFoundError,
)
from app.shared.countries import UnsupportedCountryError

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    EmployeeNotFoundError: 404,
    DuplicateEmailError: 409,
    CurrencyChangeRequiresSalaryError: 422,
    UnsupportedCountryError: 422,
}


def register_error_handlers(app: FastAPI) -> None:
    for error, status in _STATUS_BY_ERROR.items():
        app.add_exception_handler(error, _handler(status))

    async def llm_unavailable(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "The AI assistant is unavailable right now. Is Ollama running?"},
        )

    app.add_exception_handler(LLMUnavailableError, llm_unavailable)


def _handler(status: int):
    async def handle(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status, content={"detail": str(exc)})

    return handle
