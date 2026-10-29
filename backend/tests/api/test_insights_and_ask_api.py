from app.ai.llm import LLMUnavailableError


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
