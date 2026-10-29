from tests.api.conftest import EMPLOYEE


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_create_returns_employee_with_derived_currency(create_employee):
    body = create_employee()
    assert body["id"] > 0
    assert body["currency"] == "GBP"


def test_create_with_invalid_payload_returns_422_with_field(client):
    response = client.post("/api/employees", json={**EMPLOYEE, "country": "Atlantis"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "country"


def test_create_duplicate_email_returns_409(client, create_employee):
    create_employee()
    response = client.post("/api/employees", json=EMPLOYEE)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_get_missing_employee_returns_404(client):
    assert client.get("/api/employees/42").status_code == 404


def test_list_supports_filters_paging_and_sorting(client, create_employee):
    create_employee(email="a@example.com", annual_salary=50000)
    create_employee(email="b@example.com", annual_salary=90000)
    create_employee(email="c@example.com", country="India", annual_salary=2000000)

    response = client.get(
        "/api/employees",
        params={
            "country": "United Kingdom",
            "sort": "annual_salary",
            "order": "desc",
            "page": 1,
            "page_size": 1,
        },
    )

    body = response.json()
    assert body["total"] == 2
    assert body["page_size"] == 1
    assert [e["annual_salary"] for e in body["items"]] == [90000]


def test_list_rejects_oversized_page(client):
    assert client.get("/api/employees", params={"page_size": 1000}).status_code == 422


def test_patch_salary_records_history(client, create_employee):
    employee = create_employee()

    response = client.patch(
        f"/api/employees/{employee['id']}",
        json={"annual_salary": 88000, "salary_change_reason": "Annual review"},
    )
    history = client.get(f"/api/employees/{employee['id']}/salary-history").json()

    assert response.json()["annual_salary"] == 88000
    assert history[0]["previous_salary"] == 80000
    assert history[0]["reason"] == "Annual review"


def test_patch_currency_change_without_salary_is_422(client, create_employee):
    employee = create_employee()
    response = client.patch(f"/api/employees/{employee['id']}", json={"country": "India"})
    assert response.status_code == 422
    assert "INR" in response.json()["detail"]


def test_delete_returns_204_then_404(client, create_employee):
    employee = create_employee()
    assert client.delete(f"/api/employees/{employee['id']}").status_code == 204
    assert client.get(f"/api/employees/{employee['id']}").status_code == 404


def test_meta_lists_countries_and_existing_values(client, create_employee):
    create_employee()
    meta = client.get("/api/meta").json()

    assert {"name": "India", "currency": "INR"} in meta["countries"]
    assert meta["departments"] == ["Engineering"]
    assert meta["job_titles"] == ["Software Engineer"]
