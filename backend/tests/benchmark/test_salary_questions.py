"""Success criterion: the predefined business questions get accurate, reproducible answers,
verified against known seeded data.

The database is seeded with the real generator (fixed seed). Every expected value is
recomputed here in plain Python from the generator's own output (the oracle), independently of
the SQL that produces the answer. The model's choice is fixed to what a model that understood
the question returns (questions.py); live.py checks real models make that choice.
"""

import random
import statistics
from collections import defaultdict
from collections.abc import Iterator
from datetime import date

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.core.actor import VIEW_INDIVIDUAL_PAY, Actor
from app.modules.assistant.service import AskService
from app.seed.generator import (
    HISTORY_END,
    generate_employees,
    generate_salary_history,
    load_names,
)
from app.seed.run import seed_database
from app.shared.countries import to_usd
from app.shared.levels import JOB_LEVELS
from tests.benchmark.questions import QUESTIONS, BenchmarkQuestion

SEED, COUNT = 42, 2_000
HR_MANAGER = Actor(name="HR Manager", permissions=frozenset({VIEW_INDIVIDUAL_PAY}))


class ExpectedSelection:
    def __init__(self, question: BenchmarkQuestion) -> None:
        self._intent = question.intent

    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        return self._intent


@pytest.fixture(scope="module")
def seeded(engine: Engine) -> Iterator[Session]:
    """Seeded once for the module, rolled back afterwards."""
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        seed_database(session, count=COUNT, seed=SEED)
        yield session
        session.close()
        transaction.rollback()


@pytest.fixture(scope="module")
def oracle() -> tuple[list[dict], list[dict]]:
    """The same rows the seed inserted, straight from the generator."""
    rng = random.Random(SEED)
    first, last = load_names()
    employees = generate_employees(COUNT, rng, first, last)
    return employees, generate_salary_history(employees, rng)


def ask(session: Session, category_or_question: str):
    question = next(q for q in QUESTIONS if category_or_question in (q.question, q.category))
    service = AskService(
        session, ExpectedSelection(question), actor=HR_MANAGER, today=lambda: HISTORY_END
    )
    return service.ask(question.question)


def _q(text: str) -> str:
    return next(q.question for q in QUESTIONS if q.question.startswith(text))


def _usd_total(rows: list[dict]) -> int:
    """USD total the way payroll is reported: summed per country, then converted."""
    local: dict[str, int] = defaultdict(int)
    for r in rows:
        local[r["country"]] += r["annual_salary"]
    return sum(to_usd(total, country) for country, total in local.items())


def _by(rows: list[dict], key: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        grouped[r[key]].append(r)
    return grouped


# --- Every question --------------------------------------------------------------------------


def test_there_are_at_least_ten_predefined_questions():
    assert len(QUESTIONS) >= 10


@pytest.mark.parametrize("question", QUESTIONS, ids=lambda q: q.question)
def test_each_question_is_answered_reproducibly(seeded, question):
    first, again = ask(seeded, question.question), ask(seeded, question.question)

    assert first.kind == "answer"
    assert first.intent.metric == question.metric
    assert first.model_dump() == again.model_dump()


# --- Each answer, verified against the seeded data --------------------------------------------


def test_org_average_and_median(seeded, oracle):
    employees, _ = oracle
    average = round(_usd_total(employees) / len(employees))
    median = round(statistics.median(r["annual_salary_usd"] for r in employees))

    answer = ask(seeded, "Salary overview").answer

    assert f"average USD {average:,}, median USD {median:,}" in answer


def test_average_salary_in_engineering(seeded, oracle):
    engineering = _by(oracle[0], "department")["Engineering"]
    average = round(_usd_total(engineering) / len(engineering))
    median = round(statistics.median(r["annual_salary_usd"] for r in engineering))

    answer = ask(seeded, _q("What is the average salary in Engineering")).answer

    assert answer.startswith(
        f"Engineering: {len(engineering):,} employees, average USD {average:,} "
        f"(median USD {median:,}"
    )


def test_department_with_the_highest_median(seeded, oracle):
    medians = {
        department: round(statistics.median(r["annual_salary_usd"] for r in rows))
        for department, rows in _by(oracle[0], "department").items()
    }
    leader = max(medians, key=medians.get)

    answer = ask(seeded, _q("Which department has the highest median")).answer

    assert answer.startswith(f"{leader} has the highest median salary (USD {medians[leader]:,}).")


def test_engineering_compared_with_sales(seeded, oracle):
    departments = _by(oracle[0], "department")
    expected = {
        d: round(_usd_total(departments[d]) / len(departments[d])) for d in ("Engineering", "Sales")
    }

    rows = ask(seeded, _q("Compare Engineering and Sales")).table.rows

    assert {r["department"]: r["average_salary_usd"] for r in rows} == expected


def test_compensation_across_countries(seeded, oracle):
    expected = {
        country: (len(rows), to_usd(statistics.mean(r["annual_salary"] for r in rows), country))
        for country, rows in _by(oracle[0], "country").items()
    }

    rows = ask(seeded, "Country analysis").table.rows

    assert {r["country"]: (r["headcount"], r["average_salary_usd"]) for r in rows} == expected
    assert [r["average_salary_usd"] for r in rows] == sorted(
        (r["average_salary_usd"] for r in rows), reverse=True
    )


def test_data_analysts_in_germany(seeded, oracle):
    salaries = [
        r["annual_salary"]
        for r in oracle[0]
        if (r["job_title"], r["country"]) == ("Data Analyst", "Germany")
    ]

    answer = ask(seeded, "Role analysis").answer

    assert answer == (
        f"Data Analyst in Germany: {len(salaries)} employees, average EUR "
        f"{round(statistics.mean(salaries)):,} (min EUR {min(salaries):,}, max EUR "
        f"{max(salaries):,})."
    )


def test_like_for_like_gaps_between_levels(seeded, oracle):
    groups: dict[tuple, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for r in oracle[0]:
        groups[(r["job_title"], r["country"])][r["job_level"]].append(r["annual_salary"])
    expected = {}
    for lower, higher in zip(JOB_LEVELS, JOB_LEVELS[1:], strict=False):
        weighted = weights = 0
        for levels in groups.values():
            if lower in levels and higher in levels:
                n = len(levels[lower]) + len(levels[higher])
                ratio = statistics.median(levels[higher]) / statistics.median(levels[lower])
                weighted, weights = weighted + ratio * n, weights + n
        expected[higher] = round((weighted / weights - 1) * 100, 1)

    rows = ask(seeded, "Pay equity").table.rows

    assert {r["job_level"]: r["gap_to_previous_pct"] for r in rows[1:]} == expected


def test_outliers_against_peers(seeded, oracle):
    peers: dict[tuple, list[int]] = defaultdict(list)
    for r in oracle[0]:
        peers[(r["job_title"], r["country"], r["job_level"])].append(r["annual_salary"])
    medians = {key: statistics.median(v) for key, v in peers.items() if len(v) >= 5}
    found = []
    for index, r in enumerate(oracle[0]):  # index order is id order
        key = (r["job_title"], r["country"], r["job_level"])
        if key in medians:
            deviation = (r["annual_salary"] - medians[key]) / medians[key]
            if abs(deviation) >= 0.25:
                found.append((-abs(deviation), index, r["full_name"], round(deviation * 100, 1)))
    expected = [(name, pct) for _, _, name, pct in sorted(found)[:20]]

    rows = ask(seeded, _q("Which employees earn significantly")).table.rows

    assert len(expected) > 0
    assert [(r["full_name"], r["deviation_pct"]) for r in rows] == expected


def test_employees_above_their_department_average(seeded, oracle):
    employees = oracle[0]
    averages = {
        d: statistics.mean(r["annual_salary_usd"] for r in rows)
        for d, rows in _by(employees, "department").items()
    }
    above = sum(r["annual_salary_usd"] > averages[r["department"]] for r in employees)

    answer = ask(seeded, _q("Show employees earning above")).answer

    assert answer.startswith(f"{above:,} of {len(employees):,} employees earn above")


def test_salary_changes_over_the_last_12_months(seeded, oracle):
    window = [c for c in oracle[1] if date(2025, 10, 1) <= c["effective_date"] <= HISTORY_END]
    raises = [(c["new_salary"] - c["previous_salary"]) * 100 / c["previous_salary"] for c in window]
    people = {c["employee_index"] for c in window}

    answer = ask(seeded, "Trends").answer

    assert answer.startswith(
        f"Over the last 12 months (Oct 2025 – Sep 2026): {len(window):,} salary changes for "
        f"{len(people):,} employees, average raise {statistics.mean(raises):.1f}%."
    )


def test_salary_bands(seeded, oracle):
    bounds = [(0, 50_000), (50_000, 100_000), (100_000, 150_000), (150_000, 200_000)]
    usd = [r["annual_salary_usd"] for r in oracle[0]]
    expected = [sum(low <= s < high for s in usd) for low, high in bounds]
    expected.append(sum(s >= 200_000 for s in usd))

    rows = ask(seeded, "Distribution").table.rows

    assert [r["headcount"] for r in rows] == expected
