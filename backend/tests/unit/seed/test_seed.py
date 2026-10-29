import random
from datetime import date

from sqlalchemy import func, select

from app.modules.employees.models import Employee, SalaryChange
from app.seed.generator import (
    HISTORY_END,
    HISTORY_START,
    generate_employees,
    generate_salary_history,
    load_names,
)
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


# --- Salary history ------------------------------------------------------------------------


def _history(count=500, seed=7):
    rows = _generate(count, seed)
    return rows, generate_salary_history(rows, random.Random(seed))


def test_history_is_deterministic():
    assert _history(seed=3)[1] == _history(seed=3)[1]


def test_history_changes_fall_in_the_window_and_after_hiring():
    rows, history = _history()
    for change in history:
        hired = rows[change["employee_index"]]["hire_date"]
        assert max(HISTORY_START, hired) <= change["effective_date"] <= HISTORY_END


def test_history_chains_end_at_the_current_salary():
    rows, history = _history()
    by_employee: dict[int, list[dict]] = {}
    for change in history:
        by_employee.setdefault(change["employee_index"], []).append(change)

    for index, changes in by_employee.items():
        changes.sort(key=lambda c: c["effective_date"])
        assert changes[-1]["new_salary"] == rows[index]["annual_salary"]
        for earlier, later in zip(changes, changes[1:], strict=False):
            assert earlier["new_salary"] == later["previous_salary"]
            assert later["new_salary"] > later["previous_salary"]


def test_most_employees_had_a_raise_in_the_last_year_of_history():
    rows, history = _history(1000)
    recent = {
        c["employee_index"] for c in history if (HISTORY_END - c["effective_date"]).days < 365
    }
    assert len(recent) > 0.5 * len(rows)


def test_seed_database_stores_history_linked_to_employees(session):
    seed_database(session, count=100, seed=1)

    orphans = session.scalar(
        select(func.count()).select_from(SalaryChange).where(SalaryChange.employee_id.is_(None))
    )
    changes = session.scalar(select(func.count()).select_from(SalaryChange))
    assert changes > 50 and orphans == 0
    latest = session.scalars(
        select(SalaryChange).order_by(SalaryChange.effective_date.desc())
    ).first()
    assert latest.new_salary == session.get(Employee, latest.employee_id).annual_salary
