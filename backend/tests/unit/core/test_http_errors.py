import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import (
    BusinessRuleError,
    ConflictError,
    DomainError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.core.http_errors import register_error_handlers


class MissingWidget(NotFoundError):
    pass


class FlakyDependency(ServiceUnavailableError):
    public_message = "Widgets are temporarily unavailable."


def _client_raising(error: Exception) -> TestClient:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    def boom():
        raise error

    return TestClient(app)


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (MissingWidget("Widget 7 not found"), 404),
        (ConflictError("already exists"), 409),
        (BusinessRuleError("not allowed"), 422),
        (DomainError("generic rule broken"), 400),
    ],
)
def test_error_category_decides_status_and_message_is_returned(error, status):
    response = _client_raising(error).get("/boom")
    assert response.status_code == status
    assert response.json() == {"detail": str(error)}


def test_unavailable_dependency_hides_internal_details():
    response = _client_raising(FlakyDependency("connect to 10.0.0.5:11434 refused")).get("/boom")
    assert response.status_code == 503
    assert response.json() == {"detail": "Widgets are temporarily unavailable."}
