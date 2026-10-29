from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.dependencies import get_session
from app.main import create_app


class StubLLM:
    def __init__(self) -> None:
        self.response: dict | Exception = {"metric": "org_summary"}

    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


@pytest.fixture
def llm() -> StubLLM:
    return StubLLM()


@pytest.fixture
def make_client(postgres_url: str, session: Session, llm: StubLLM):
    """Build a TestClient whose requests share the test's rolled-back transaction."""

    def _make(**settings) -> TestClient:
        app: FastAPI = create_app(Settings(database_url=postgres_url, **settings), llm=llm)
        app.dependency_overrides[get_session] = lambda: session
        return TestClient(app)

    return _make


@pytest.fixture
def client(make_client) -> Iterator[TestClient]:
    with make_client() as c:
        yield c


EMPLOYEE = {
    "full_name": "Ada Lovelace",
    "email": "ada@example.com",
    "job_title": "Software Engineer",
    "job_level": "Mid",
    "department": "Engineering",
    "country": "United Kingdom",
    "annual_salary": 80000,
    "hire_date": "2020-01-15",
}


@pytest.fixture
def create_employee(client):
    def _create(**overrides) -> dict:
        response = client.post("/api/employees", json={**EMPLOYEE, **overrides})
        assert response.status_code == 201, response.text
        return response.json()

    return _create
