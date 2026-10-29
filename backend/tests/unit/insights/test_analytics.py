"""Pay-equity, distribution and trend analytics, on small hand-computable datasets."""

from datetime import date

import pytest

from app.modules.employees.models import SalaryChange
from app.modules.insights.service import InsightsService
from tests.conftest import build_employee


def _add(session, *rows: dict) -> InsightsService:
    session.add_all(
        build_employee(email=f"e{i}@example.com", full_name=f"Person {i}", **row)
        for i, row in enumerate(rows)
    )
    session.commit()
    return InsightsService(session)


US = dict(country="United States", currency="USD")
DE = dict(country="Germany", currency="EUR")


# --- Medians ---------------------------------------------------------------------------------


def test_org_and_department_medians_are_in_usd(session):
    insights = _add(
        session,
        dict(**US, department="Engineering", annual_salary=100_000),
        dict(**US, department="Engineering", annual_salary=300_000),
        dict(**DE, department="Sales", annual_salary=50_000),  # USD 54,000
    )

    assert insights.summary().median_salary_usd == 100_000
    by_department = {d.department: d.median_salary_usd for d in insights.department_stats()}
    assert by_department == {"Engineering": 200_000, "Sales": 54_000}
    germany = next(c for c in insights.country_stats() if c.country == "Germany")
    assert germany.median_salary_usd == 54_000


# --- Levels (pay gap) ------------------------------------------------------------------------


@pytest.fixture
def levels(session):
    return _add(
        session,
        dict(**US, job_level="Junior", annual_salary=100_000),
        dict(**US, job_level="Junior", annual_salary=110_000),
        dict(**US, job_level="Mid", annual_salary=120_000),
        dict(**US, job_level="Mid", annual_salary=130_000),
        dict(**DE, job_level="Mid", annual_salary=80_000),  # USD 86,400
        dict(**US, job_level="Senior", annual_salary=150_000),
        dict(**US, job_level="Senior", annual_salary=170_000),
    )


def test_level_stats_follow_the_ladder_with_gaps_between_medians(levels):
    junior, mid, senior = levels.level_stats()

    assert [s.job_level for s in (junior, mid, senior)] == ["Junior", "Mid", "Senior"]
    assert (junior.headcount, junior.median_salary_usd, junior.gap_to_previous_pct) == (
        2,
        105_000,
        None,
    )
    assert (mid.headcount, mid.median_salary_usd, mid.average_salary_usd) == (3, 120_000, 112_133)
    assert mid.gap_to_previous_pct == pytest.approx(14.3, abs=0.05)
    assert senior.gap_to_previous_pct == pytest.approx(33.3, abs=0.05)


def test_level_stats_can_be_narrowed_to_a_country(levels):
    stats = levels.level_stats(country="Germany")
    assert [(s.job_level, s.headcount) for s in stats] == [("Mid", 1)]


# --- Distribution ----------------------------------------------------------------------------


def test_salary_bands_count_everyone_once_in_usd(session):
    insights = _add(
        session,
        dict(**US, annual_salary=40_000),
        dict(**US, annual_salary=50_000),  # lower bound is inclusive
        dict(**US, annual_salary=149_999),
        dict(**DE, annual_salary=200_000),  # USD 216,000
        dict(country="India", currency="INR", annual_salary=2_000_000),  # USD 24,000
    )

    bands = insights.salary_bands()

    assert [(b.label, b.headcount) for b in bands] == [
        ("Under USD 50k", 2),
        ("USD 50k–100k", 1),
        ("USD 100k–150k", 1),
        ("USD 150k–200k", 0),
        ("USD 200k+", 1),
    ]


# --- Outliers --------------------------------------------------------------------------------


def test_outliers_are_measured_against_peers_with_the_same_title_level_and_country(session):
    peers = [dict(**US, job_level="Mid", annual_salary=100_000) for _ in range(4)]
    insights = _add(
        session,
        *peers,
        dict(**US, job_level="Mid", annual_salary=150_000),  # +50% vs peer median 100k
        dict(**US, job_level="Mid", annual_salary=90_000),  # -10%: within tolerance
        # Same pay, but a different level: not a peer of the group above.
        dict(**US, job_level="Senior", annual_salary=150_000),
    )

    [outlier] = insights.outliers(threshold_pct=25, min_peers=3)

    assert outlier.annual_salary == 150_000
    assert outlier.peer_median_salary == 100_000
    assert outlier.deviation_pct == pytest.approx(50.0)
    assert (outlier.job_level, outlier.peer_count) == ("Mid", 6)


def test_small_peer_groups_never_produce_outliers(session):
    insights = _add(
        session,
        dict(**US, annual_salary=100_000),
        dict(**US, annual_salary=300_000),
    )
    assert insights.outliers(threshold_pct=25, min_peers=3) == []


# --- Above department average ----------------------------------------------------------------


def test_employees_above_their_department_average_in_usd(session):
    insights = _add(
        session,
        dict(**US, department="Engineering", annual_salary=100_000),
        dict(**US, department="Engineering", annual_salary=200_000),
        dict(**US, department="Engineering", annual_salary=150_000),  # equal: not above
        dict(**US, department="Sales", annual_salary=50_000),
        dict(**US, department="Sales", annual_salary=70_000),
    )

    report = insights.above_department_average()

    assert (report.employees_above, report.headcount) == (2, 5)
    assert [(d.department, d.above, d.average_salary_usd) for d in report.departments] == [
        ("Engineering", 1, 150_000),
        ("Sales", 1, 60_000),
    ]
    assert [(e.department, e.above_by_usd) for e in report.top] == [
        ("Engineering", 50_000),
        ("Sales", 10_000),
    ]


# --- Trends ----------------------------------------------------------------------------------


def _change(employee, effective: date, previous: int, new: int, currency=("USD", "USD")):
    return SalaryChange(
        employee=employee,
        previous_salary=previous,
        new_salary=new,
        previous_currency=currency[0],
        new_currency=currency[1],
        effective_date=effective,
        changed_by="test",
    )


def test_trends_cover_the_last_12_months_including_quiet_ones(session):
    ada, bob = build_employee(email="ada@example.com"), build_employee(email="bob@example.com")
    session.add_all(
        [
            _change(ada, date(2024, 12, 1), 90_000, 100_000),  # before the window
            _change(ada, date(2026, 3, 15), 100_000, 110_000),  # +10%
            _change(bob, date(2026, 3, 20), 50_000, 60_000, ("EUR", "GBP")),  # not a raise %
            _change(ada, date(2026, 9, 1), 110_000, 114_400),  # +4%
            _change(bob, date(2026, 9, 30), 60_000, 63_600),  # +6%
        ]
    )
    session.commit()

    trend = InsightsService(session).salary_trends(as_of=date(2026, 9, 30))

    assert [m.month for m in trend.months] == [f"2025-{m}" for m in ("10", "11", "12")] + [
        f"2026-{m:02}" for m in range(1, 10)
    ]
    by_month = {m.month: m for m in trend.months}
    assert (by_month["2026-03"].changes, by_month["2026-03"].average_raise_pct) == (2, 10.0)
    assert by_month["2026-09"].average_raise_pct == pytest.approx(5.0)
    assert (by_month["2025-10"].changes, by_month["2025-10"].average_raise_pct) == (0, None)
    assert (trend.changes, trend.employees) == (4, 2)
    assert trend.average_raise_pct == 6.7  # (10 + 4 + 6) / 3, reported to one decimal
