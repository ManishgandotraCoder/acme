"""Every read path the app uses must be served by an index (see docs/adr/0006-indexing.md).

These run the real repository/service calls and inspect PostgreSQL's EXPLAIN plans, so a
query change that silently falls back to a full table scan or an in-memory sort fails CI.
"""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.actor import SYSTEM
from app.modules.employees.repository import EmployeeFilter, EmployeeRepository, SortField
from app.modules.employees.service import EmployeeService
from app.modules.insights.service import InsightsService
from app.seed.run import seed_database
from tests.query_plans import query_plans, sorts, table_scans


@pytest.fixture
def seeded(session):
    seed_database(session, count=300, seed=1)  # employees + salary history
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
    "list filtered by job level": lambda s, eid: repo(s).search(EmployeeFilter(job_level="Lead")),
    "list filtered by currency": lambda s, eid: repo(s).search(EmployeeFilter(currency="EUR")),
    "list filtered by USD salary range": lambda s, eid: repo(s).search(
        EmployeeFilter(salary_min=150_000, salary_max=200_000)
    ),
    "list filtered by country and local salary range": lambda s, eid: repo(s).search(
        EmployeeFilter(country="India", salary_min=3_000_000)
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
    "salary history": lambda s, eid: EmployeeService(s, actor=SYSTEM).salary_history(eid),
    "insights summary": lambda s, eid: InsightsService(s).summary(),
    "insights by country": lambda s, eid: InsightsService(s).country_stats(),
    "insights by job title": lambda s, eid: InsightsService(s).job_title_stats("Germany"),
    "insights by department": lambda s, eid: InsightsService(s).department_stats(),
    "insights by department in a country": lambda s, eid: InsightsService(s).department_stats(
        "India"
    ),
    "pay by level": lambda s, eid: InsightsService(s).level_stats(),
    "pay by level for a role in a country": lambda s, eid: InsightsService(s).level_stats(
        job_title="Software Engineer", country="India"
    ),
    "salary bands": lambda s, eid: InsightsService(s).salary_bands(),
    "salary trends": lambda s, eid: InsightsService(s).salary_trends(as_of=date(2026, 9, 30)),
}

# Ranking computed values (deviation from peers, distance above an average) needs a final
# top-N sort; the inputs must still come from indexes.
RANKED_READ_PATHS = {
    "outliers": lambda s: InsightsService(s).outliers(),
    "above department average": lambda s: InsightsService(s).above_department_average(),
}


@pytest.mark.parametrize("name", READ_PATHS)
def test_read_path_uses_indexes_without_full_scans_or_sorts(seeded, employee_id, name):
    plans = query_plans(seeded, lambda: READ_PATHS[name](seeded, employee_id))
    assert table_scans(plans) + sorts(plans) == [], [str(n) for n in plans]


@pytest.mark.parametrize("name", RANKED_READ_PATHS)
def test_ranked_read_path_reads_through_indexes(seeded, name):
    plans = query_plans(seeded, lambda: RANKED_READ_PATHS[name](seeded), allow_sort=True)
    assert table_scans(plans) == [], [str(n) for n in plans]


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


def test_plan_check_is_not_fooled_by_table_bloat_from_other_tests(session, engine):
    # Regression: a rolled-back bulk insert elsewhere (the benchmark) leaves dead rows; the
    # planner then sized the table differently and chose another index plus an *incremental*
    # sort, which enable_sort does not disable. The check must still find the sort-free path.
    with engine.connect() as other, other.begin() as transaction:
        seed_database(Session(bind=other), count=2_000, seed=3)
        transaction.rollback()
    seed_database(session, count=300, seed=1)

    plans = query_plans(session, lambda: InsightsService(session).level_stats())

    assert sorts(plans) == [], [str(n) for n in plans]
