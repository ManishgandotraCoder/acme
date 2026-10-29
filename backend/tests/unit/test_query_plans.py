"""Every read path the app uses must be served by an index (see docs/adr/0006-indexing.md).

These run the real repository/service calls and inspect SQLite's EXPLAIN QUERY PLAN, so a
query change that silently falls back to a full table scan or an in-memory sort fails CI.
"""

import random

import pytest

from app.modules.employees.repository import EmployeeFilter, EmployeeRepository, SortField
from app.modules.employees.service import EmployeeService
from app.modules.insights.service import InsightsService
from app.seed.generator import generate_employees, load_names
from tests.query_plans import full_scans_and_sorts, query_plans


@pytest.fixture
def seeded(session):
    from app.modules.employees.models import Employee

    first, last = load_names()
    session.add_all(
        Employee(**row) for row in generate_employees(300, random.Random(1), first, last)
    )
    session.commit()
    return session


repo = EmployeeRepository

READ_PATHS = {
    "list, default name sort": lambda s: repo(s).search(EmployeeFilter()),
    "list filtered by country": lambda s: repo(s).search(EmployeeFilter(country="India")),
    "list filtered by department": lambda s: repo(s).search(EmployeeFilter(department="Sales")),
    "list filtered by job title": lambda s: repo(s).search(EmployeeFilter(job_title="Recruiter")),
    "sort by salary (USD)": lambda s: repo(s).search(
        EmployeeFilter(), sort=SortField.ANNUAL_SALARY, descending=True
    ),
    "list filtered by country, sorted by salary": lambda s: repo(s).search(
        EmployeeFilter(country="India"), sort=SortField.ANNUAL_SALARY, descending=True
    ),
    "sort by hire date": lambda s: repo(s).search(
        EmployeeFilter(), sort=SortField.HIRE_DATE, descending=True
    ),
    "get by id": lambda s: repo(s).get(7),
    "get by email": lambda s: repo(s).get_by_email("Someone@Example.com"),
    "salary history": lambda s: EmployeeService(s).salary_history(7),
    "insights summary": lambda s: InsightsService(s).summary(),
    "insights by country": lambda s: InsightsService(s).country_stats(),
    "insights by job title": lambda s: InsightsService(s).job_title_stats("Germany"),
    "insights by department": lambda s: InsightsService(s).department_stats(),
    "insights by department in a country": lambda s: InsightsService(s).department_stats("India"),
}


@pytest.mark.parametrize("name", READ_PATHS)
def test_read_path_uses_indexes_without_full_scans_or_sorts(seeded, name):
    plans = query_plans(seeded, lambda: READ_PATHS[name](seeded))
    assert full_scans_and_sorts(plans) == [], plans


def test_email_lookup_uses_the_unique_index(seeded):
    plans = query_plans(seeded, lambda: repo(seeded).get_by_email("a@example.com"))
    assert any("(email=?)" in step for step in plans), plans


def test_search_uses_the_full_text_index_instead_of_scanning(seeded):
    plans = query_plans(seeded, lambda: repo(seeded).search(EmployeeFilter(search="patel")))

    assert any("employees_search VIRTUAL TABLE" in step for step in plans), plans
    # Matches are fetched by primary key; only the small matched set is sorted.
    table_scans = [step for step in full_scans_and_sorts(plans) if "TEMP B-TREE" not in step]
    assert table_scans == [], plans
