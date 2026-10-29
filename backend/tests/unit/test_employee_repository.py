from app.repositories.employee_repository import EmployeeFilter, EmployeeRepository, SortField
from tests.conftest import build_employee


def _seed(session, *employees):
    session.add_all(employees)
    session.commit()


def test_add_and_get_employee(session):
    repo = EmployeeRepository(session)
    created = repo.add(build_employee())
    session.commit()

    assert repo.get(created.id).email == "ada@acme.test"


def test_get_by_email_is_case_insensitive(session):
    _seed(session, build_employee(email="ada@acme.test"))
    assert EmployeeRepository(session).get_by_email("ADA@acme.test") is not None


def test_list_paginates_and_reports_total(session):
    _seed(session, *[build_employee(full_name=f"E{i:02}", email=f"e{i}@acme.test") for i in range(25)])

    items, total = EmployeeRepository(session).search(EmployeeFilter(), page=2, page_size=10)

    assert total == 25
    assert [e.full_name for e in items] == [f"E{i:02}" for i in range(10, 20)]


def test_list_searches_name_and_email(session):
    _seed(
        session,
        build_employee(full_name="Grace Hopper", email="grace@acme.test"),
        build_employee(full_name="Alan Turing", email="alan@acme.test"),
    )
    repo = EmployeeRepository(session)

    assert [e.full_name for e in repo.search(EmployeeFilter(search="hop"))[0]] == ["Grace Hopper"]
    assert [e.full_name for e in repo.search(EmployeeFilter(search="alan@"))[0]] == ["Alan Turing"]


def test_list_filters_by_country_department_and_job_title(session):
    _seed(
        session,
        build_employee(email="a@x.test", country="India", currency="INR", department="Sales"),
        build_employee(email="b@x.test", country="India", currency="INR", job_title="Analyst"),
        build_employee(email="c@x.test", country="Germany", currency="EUR"),
    )
    repo = EmployeeRepository(session)

    assert repo.search(EmployeeFilter(country="India"))[1] == 2
    assert repo.search(EmployeeFilter(country="India", department="Sales"))[1] == 1
    assert repo.search(EmployeeFilter(job_title="Analyst"))[1] == 1


def test_list_sorts_by_salary_descending(session):
    _seed(
        session,
        build_employee(email="a@x.test", annual_salary=50_000),
        build_employee(email="b@x.test", annual_salary=90_000),
        build_employee(email="c@x.test", annual_salary=70_000),
    )

    items, _ = EmployeeRepository(session).search(
        EmployeeFilter(), sort=SortField.ANNUAL_SALARY, descending=True
    )

    assert [e.annual_salary for e in items] == [90_000, 70_000, 50_000]


def test_distinct_values_feed_filter_dropdowns(session):
    _seed(
        session,
        build_employee(email="a@x.test", department="Sales", job_title="Account Executive"),
        build_employee(email="b@x.test", department="Engineering"),
        build_employee(email="c@x.test", department="Sales", job_title="Account Executive"),
    )
    repo = EmployeeRepository(session)

    assert repo.distinct_departments() == ["Engineering", "Sales"]
    assert repo.distinct_job_titles() == ["Account Executive", "Software Engineer"]


def test_delete_removes_employee(session):
    repo = EmployeeRepository(session)
    employee = repo.add(build_employee())
    session.commit()

    repo.delete(employee)
    session.commit()

    assert repo.get(employee.id) is None
