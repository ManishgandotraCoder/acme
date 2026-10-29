import pytest

from app.modules.employees.repository import EmployeeFilter, EmployeeRepository, SortField
from tests.conftest import build_employee


def _seed(session, *employees):
    session.add_all(employees)
    session.commit()


def test_add_and_get_employee(session):
    repo = EmployeeRepository(session)
    created = repo.add(build_employee())
    session.commit()

    assert repo.get(created.id).email == "ada@example.com"


def test_get_by_email_is_case_insensitive(session):
    _seed(session, build_employee(email="ada@example.com"))
    assert EmployeeRepository(session).get_by_email("ADA@example.com") is not None


def test_list_paginates_and_reports_total(session):
    _seed(
        session,
        *[build_employee(full_name=f"E{i:02}", email=f"e{i}@example.com") for i in range(25)],
    )

    items, total = EmployeeRepository(session).search(EmployeeFilter(), page=2, page_size=10)

    assert total == 25
    assert [e.full_name for e in items] == [f"E{i:02}" for i in range(10, 20)]


def test_list_searches_name_and_email(session):
    _seed(
        session,
        build_employee(full_name="Grace Hopper", email="grace@example.com"),
        build_employee(full_name="Alan Turing", email="alan@example.com"),
    )
    repo = EmployeeRepository(session)

    assert [e.full_name for e in repo.search(EmployeeFilter(search="hop"))[0]] == ["Grace Hopper"]
    assert [e.full_name for e in repo.search(EmployeeFilter(search="alan@"))[0]] == ["Alan Turing"]


def test_list_filters_by_country_department_and_job_title(session):
    _seed(
        session,
        build_employee(email="a@example.com", country="India", currency="INR", department="Sales"),
        build_employee(email="b@example.com", country="India", currency="INR", job_title="Analyst"),
        build_employee(email="c@example.com", country="Germany", currency="EUR"),
    )
    repo = EmployeeRepository(session)

    assert repo.search(EmployeeFilter(country="India"))[1] == 2
    assert repo.search(EmployeeFilter(country="India", department="Sales"))[1] == 1
    assert repo.search(EmployeeFilter(job_title="Analyst"))[1] == 1


def test_list_sorts_by_salary_descending(session):
    _seed(
        session,
        build_employee(email="a@example.com", annual_salary=50_000),
        build_employee(email="b@example.com", annual_salary=90_000),
        build_employee(email="c@example.com", annual_salary=70_000),
    )

    items, _ = EmployeeRepository(session).search(
        EmployeeFilter(), sort=SortField.ANNUAL_SALARY, descending=True
    )

    assert [e.annual_salary for e in items] == [90_000, 70_000, 50_000]


def test_distinct_values_feed_filter_dropdowns(session):
    _seed(
        session,
        build_employee(email="a@example.com", department="Sales", job_title="Account Executive"),
        build_employee(email="b@example.com", department="Engineering"),
        build_employee(email="c@example.com", department="Sales", job_title="Account Executive"),
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


def test_salary_sort_compares_across_currencies_in_usd(session):
    _seed(
        session,
        # 5,000,000 INR ~= 60,000 USD -- numerically largest, but not the best paid.
        build_employee(
            email="a@example.com", country="India", currency="INR", annual_salary=5_000_000
        ),
        build_employee(
            email="b@example.com", country="United States", currency="USD", annual_salary=90_000
        ),
        build_employee(
            email="c@example.com", country="Germany", currency="EUR", annual_salary=70_000
        ),
    )

    items, _ = EmployeeRepository(session).search(
        EmployeeFilter(), sort=SortField.ANNUAL_SALARY, descending=True
    )

    assert [e.country for e in items] == ["United States", "Germany", "India"]


# --- Substring search (pg_trgm) ------------------------------------------------------------


def _names(repo, term):
    return sorted(e.full_name for e in repo.search(EmployeeFilter(search=term))[0])


def test_search_matches_substrings_case_insensitively(session):
    _seed(session, build_employee(full_name="Priya Patel", email="priya.patel@example.com"))
    repo = EmployeeRepository(session)

    assert _names(repo, "ATEL") == ["Priya Patel"]
    assert _names(repo, "iya.pa") == ["Priya Patel"]  # matches inside the email


def test_short_terms_still_match(session):
    _seed(session, build_employee(full_name="Bo Li", email="bo@example.com"))
    assert _names(EmployeeRepository(session), "Li") == ["Bo Li"]


def test_search_follows_renames_and_deletes(session):
    repo = EmployeeRepository(session)
    employee = repo.add(build_employee(full_name="Grace Hopper"))
    session.commit()

    employee.full_name = "Grace Brewster"
    session.commit()
    assert _names(repo, "hopper") == []
    assert _names(repo, "brewster") == ["Grace Brewster"]

    repo.delete(employee)
    session.commit()
    assert _names(repo, "brewster") == []


@pytest.mark.parametrize("term", ["%", "_", "%a%", "a_a", "'; DROP", '"quoted"', "x*"])
def test_search_input_is_never_interpreted_as_query_syntax(session, term):
    _seed(session, build_employee())
    assert EmployeeRepository(session).search(EmployeeFilter(search=term))[1] == 0


def test_salary_sort_within_one_country_matches_usd_order(session):
    _seed(
        session,
        build_employee(email="a@example.com", country="India", currency="INR", annual_salary=950),
        build_employee(email="b@example.com", country="India", currency="INR", annual_salary=900),
    )
    # Both round to USD 11 and the id tie-breaker would put 900 first; only the local
    # amount orders them correctly.
    items, _ = EmployeeRepository(session).search(
        EmployeeFilter(country="India"), sort=SortField.ANNUAL_SALARY, descending=True
    )
    assert [e.annual_salary for e in items] == [950, 900]


# --- Level, currency and salary-range filters -----------------------------------------------


def _names_matching(session, **filters) -> list[str]:
    items, _ = EmployeeRepository(session).search(EmployeeFilter(**filters))
    return [e.full_name for e in items]


@pytest.fixture
def mixed_currencies(session):
    _seed(
        session,
        build_employee(
            full_name="Anna",
            email="anna@example.com",
            country="Germany",
            currency="EUR",
            annual_salary=70_000,
            job_level="Senior",
        ),
        build_employee(
            full_name="Jean",
            email="jean@example.com",
            country="France",
            currency="EUR",
            annual_salary=50_000,
            job_level="Mid",
        ),
        build_employee(
            full_name="Ravi",
            email="ravi@example.com",
            country="India",
            currency="INR",
            annual_salary=5_000_000,
            job_level="Senior",
        ),
        build_employee(
            full_name="Sam",
            email="sam@example.com",
            country="United States",
            currency="USD",
            annual_salary=60_000,
            job_level="Junior",
        ),
    )
    return session


def test_filters_by_job_level(mixed_currencies):
    assert _names_matching(mixed_currencies, job_level="Senior") == ["Anna", "Ravi"]


def test_currency_filter_spans_every_country_using_it(mixed_currencies):
    assert _names_matching(mixed_currencies, currency="EUR") == ["Anna", "Jean"]


def test_salary_range_compares_in_usd_when_currencies_are_mixed(mixed_currencies):
    # INR 5,000,000 is about USD 60,000: in range, although the raw number is far above it.
    assert _names_matching(mixed_currencies, salary_min=55_000, salary_max=65_000) == [
        "Ravi",
        "Sam",
    ]


def test_salary_range_uses_local_amounts_once_one_currency_is_chosen(mixed_currencies):
    assert _names_matching(mixed_currencies, currency="EUR", salary_min=60_000) == ["Anna"]
    assert _names_matching(mixed_currencies, country="India", salary_max=6_000_000) == ["Ravi"]
