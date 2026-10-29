from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
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
def client(llm) -> Iterator[TestClient]:
    app = create_app(Settings(database_url="sqlite://"), llm=llm)
    with TestClient(app) as c:
        yield c


EMPLOYEE = {
    "full_name": "Ada Lovelace",
    "email": "ada@example.com",
    "job_title": "Software Engineer",
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
