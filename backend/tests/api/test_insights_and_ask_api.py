import pytest

from app.modules.assistant.llm import LLMUnavailableError


def test_insight_endpoints(client, create_employee):
    create_employee(email="a@example.com", country="India", annual_salary=1_000_000)
    create_employee(email="b@example.com", country="India", annual_salary=3_000_000)

    assert client.get("/api/insights/summary").json()["headcount"] == 2
    assert client.get("/api/insights/countries").json()[0]["median_salary"] == 2_000_000
    titles = client.get("/api/insights/job-titles", params={"country": "India"}).json()
    assert titles[0]["job_title"] == "Software Engineer"
    departments = client.get("/api/insights/departments").json()
    assert departments[0]["headcount"] == 2


def test_job_title_insights_require_supported_country(client):
    response = client.get("/api/insights/job-titles", params={"country": "Atlantis"})
    assert response.status_code == 422


def test_ask_returns_grounded_answer(client, create_employee, llm):
    create_employee()
    llm.response = {"metric": "org_summary"}

    body = client.post("/api/ask", json={"question": "How many people do we employ?"}).json()

    assert body["intent"]["metric"] == "org_summary"
    assert body["answer"].startswith("ACME has 1 employee across 1 country")


def test_ask_returns_503_when_llm_is_down(client, llm):
    llm.response = LLMUnavailableError("connection refused")
    response = client.post("/api/ask", json={"question": "Average pay?"})
    assert response.status_code == 503
    assert "AI assistant" in response.json()["detail"]


def test_ask_rejects_blank_question(client):
    assert client.post("/api/ask", json={"question": "  "}).status_code == 422


def test_pay_equity_distribution_and_trend_endpoints(client, create_employee):
    create_employee()

    assert client.get("/api/insights/levels").json()[0]["job_level"] == "Mid"
    assert sum(b["headcount"] for b in client.get("/api/insights/salary-bands").json()) == 1
    trend = client.get("/api/insights/salary-trends", params={"as_of": "2026-09-30"}).json()
    assert len(trend["months"]) == 12
    assert client.get("/api/insights/outliers").json() == []
    assert client.get("/api/insights/above-department-average").json()["headcount"] == 1


@pytest.mark.parametrize(
    "path", ["/api/insights/outliers", "/api/insights/above-department-average"]
)
def test_individual_level_insights_need_permission(make_client, path):
    with make_client(actor_permissions=[]) as client:
        response = client.get(path)

    assert response.status_code == 403
    assert "individual" in response.json()["detail"]


def test_lists_configured_model_providers_with_the_default(client):
    providers = client.get("/api/assistant/providers").json()
    assert [(p["id"], p["default"]) for p in providers] == [("ollama", True), ("openai", False)]


def test_a_question_can_choose_a_configured_provider(client, create_employee, llm, cloud_llm):
    create_employee()
    llm.response = LLMUnavailableError("would fail if used")
    cloud_llm.response = {"metric": "org_summary"}

    body = client.post("/api/ask", json={"question": "Headcount?", "provider": "openai"}).json()

    assert body["provider"] == "openai"
    assert body["answer"].startswith("ACME has 1 employee")


def test_choosing_an_unconfigured_provider_is_422(client):
    response = client.post("/api/ask", json={"question": "Headcount?", "provider": "anthropic"})
    assert response.status_code == 422
    assert "ollama, openai" in response.json()["detail"]
