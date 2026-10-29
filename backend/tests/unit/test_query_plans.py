"""Every read path the app uses must be served by an index (see docs/adr/0006-indexing.md).

These run the real repository/service calls and inspect PostgreSQL's EXPLAIN plans, so a
query change that silently falls back to a full table scan or an in-memory sort fails CI.
"""

import random

import pytest
from sqlalchemy import select

from app.modules.employees.repository import EmployeeFilter, EmployeeRepository, SortField
from app.modules.employees.service import EmployeeService
from app.modules.insights.service import InsightsService
from app.seed.generator import generate_employees, load_names
from tests.query_plans import query_plans, sorts, table_scans


@pytest.fixture
def seeded(session):
    from app.modules.employees.models import Employee

    first, last = load_names()
    session.add_all(
        Employee(**row) for row in generate_employees(300, random.Random(1), first, last)
    )
    session.commit()
    return session


@pytest.fixture
def employee_id(seeded) -> int:
    # Rolled-back tests don't rewind sequences, so never assume ids.
    from app.modules.employees.models import Employee

    return seeded.scalar(select(Employee.id).limit(1))


repo = EmployeeRepository

READ_PATHS = {
    "list, default name sort": lambda s, eid: repo(s).search(EmployeeFilter()),
    "list filtered by country": lambda s, eid: repo(s).search(EmployeeFilter(country="India")),
    "list filtered by department": lambda s, eid: repo(s).search(
        EmployeeFilter(department="Sales")
    ),
    "list filtered by job title": lambda s, eid: repo(s).search(
        EmployeeFilter(job_title="Recruiter")
    ),
    "sort by salary (USD)": lambda s, eid: repo(s).search(
        EmployeeFilter(), sort=SortField.ANNUAL_SALARY, descending=True
    ),
    "list filtered by country, sorted by salary": lambda s, eid: repo(s).search(
        EmployeeFilter(country="India"), sort=SortField.ANNUAL_SALARY, descending=True
    ),
    "sort by hire date": lambda s, eid: repo(s).search(
        EmployeeFilter(), sort=SortField.HIRE_DATE, descending=True
    ),
    "get by id": lambda s, eid: repo(s).get(eid),
    "get by email": lambda s, eid: repo(s).get_by_email("Someone@Example.com"),
    "salary history": lambda s, eid: EmployeeService(s).salary_history(eid),
    "insights summary": lambda s, eid: InsightsService(s).summary(),
    "insights by country": lambda s, eid: InsightsService(s).country_stats(),
    "insights by job title": lambda s, eid: InsightsService(s).job_title_stats("Germany"),
    "insights by department": lambda s, eid: InsightsService(s).department_stats(),
    "insights by department in a country": lambda s, eid: InsightsService(s).department_stats(
        "India"
    ),
}


@pytest.mark.parametrize("name", READ_PATHS)
def test_read_path_uses_indexes_without_full_scans_or_sorts(seeded, employee_id, name):
    plans = query_plans(seeded, lambda: READ_PATHS[name](seeded, employee_id))
    assert table_scans(plans) + sorts(plans) == [], [str(n) for n in plans]


def test_email_lookup_uses_the_unique_index(seeded):
    plans = query_plans(seeded, lambda: repo(seeded).get_by_email("a@example.com"))
    assert any(n.index == "employees_email_key" for n in plans), [str(n) for n in plans]


def test_search_uses_the_trigram_indexes_instead_of_scanning(seeded):
    plans = query_plans(
        seeded, lambda: repo(seeded).search(EmployeeFilter(search="patel")), allow_sort=True
    )

    used = {n.index for n in plans}
    assert {"ix_employees_full_name_trgm", "ix_employees_email_trgm"} <= used, used
    # Matches come from the indexes; only the small matched set is sorted.
    assert table_scans(plans) == [], [str(n) for n in plans]
