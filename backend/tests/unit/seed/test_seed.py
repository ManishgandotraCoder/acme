import random
from datetime import date

from sqlalchemy import func, select

from app.modules.employees.models import Employee
from app.seed.generator import generate_employees, load_names
from app.seed.run import seed_database
from app.shared.countries import currency_for
from app.shared.levels import JOB_LEVELS, level_rank

FIRST = ["Ada", "Alan", "Grace"]
LAST = ["Hopper", "Turing", "Lovelace"]


def _generate(count=200, seed=7):
    return generate_employees(count, random.Random(seed), FIRST, LAST)


def test_generates_exact_count_with_unique_emails():
    rows = _generate(200)
    assert len(rows) == 200
    assert len({r["email"] for r in rows}) == 200


def test_same_seed_produces_identical_data():
    assert _generate(seed=1) == _generate(seed=1)
    assert _generate(seed=1) != _generate(seed=2)


def test_rows_are_valid_employees():
    for row in _generate(500):
        assert row["currency"] == currency_for(row["country"])
        assert row["annual_salary"] > 0
        assert date(2010, 1, 1) <= row["hire_date"] <= date.today()
        first, last = row["full_name"].split(" ")
        assert first in FIRST and last in LAST


def test_every_employee_has_a_job_level_and_all_levels_occur():
    rows = _generate(500)
    assert {r["job_level"] for r in rows} == set(JOB_LEVELS)


def test_higher_levels_are_paid_more_within_the_same_role_and_country():
    rows = [
        r
        for r in _generate(3000)
        if (r["job_title"], r["country"]) == ("Software Engineer", "United States")
    ]
    by_level: dict[str, list[int]] = {}
    for r in rows:
        by_level.setdefault(r["job_level"], []).append(r["annual_salary"])
    averages = [
        sum(v) / len(v) for _, v in sorted(by_level.items(), key=lambda kv: level_rank(kv[0]))
    ]
    assert averages == sorted(averages)


def test_name_files_ship_with_enough_names_for_variety():
    first, last = load_names()
    assert len(first) * len(last) >= 10_000


def test_seed_database_inserts_and_reset_replaces(session):
    assert seed_database(session, count=50, seed=1) == 50
    assert seed_database(session, count=30, seed=1, reset=True) == 30
    assert session.scalar(select(func.count()).select_from(Employee)) == 30


def test_seed_if_empty_does_not_duplicate_existing_data(session):
    seed_database(session, count=20, seed=1)
    assert seed_database(session, count=50, seed=1, only_if_empty=True) == 0
    assert session.scalar(select(func.count()).select_from(Employee)) == 20
