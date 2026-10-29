import pytest

from app.domain.countries import UnsupportedCountryError
from app.services.insights_service import InsightsService
from tests.conftest import build_employee


@pytest.fixture
def insights(session):
    """Small, hand-computable dataset across two currencies."""
    rows = [
        # country, currency, job_title, department, salary
        ("India", "INR", "Software Engineer", "Engineering", 1_000_000),
        ("India", "INR", "Software Engineer", "Engineering", 3_000_000),
        ("India", "INR", "Data Analyst", "Finance", 2_000_000),
        ("United States", "USD", "Software Engineer", "Engineering", 150_000),
        ("United States", "USD", "Data Analyst", "Finance", 90_000),
    ]
    session.add_all(
        build_employee(
            email=f"e{i}@example.com",
            country=c,
            currency=cur,
            job_title=jt,
            department=d,
            annual_salary=s,
        )
        for i, (c, cur, jt, d, s) in enumerate(rows)
    )
    session.commit()
    return InsightsService(session)


def test_summary_reports_headcount_and_usd_payroll(insights):
    summary = insights.summary()

    # India: 6,000,000 INR * 0.012 = 72,000 USD; US: 240,000 USD
    assert summary.headcount == 5
    assert summary.country_count == 2
    assert summary.total_payroll_usd == 312_000
    assert summary.average_salary_usd == 62_400


def test_summary_of_empty_org_is_zero(session):
    summary = InsightsService(session).summary()
    assert (summary.headcount, summary.total_payroll_usd, summary.average_salary_usd) == (0, 0, 0)


def test_country_stats_in_local_currency_with_usd_average(insights):
    india, us = insights.country_stats()

    assert india.country == "India"
    assert india.currency == "INR"
    assert (india.headcount, india.min_salary, india.max_salary) == (3, 1_000_000, 3_000_000)
    assert india.average_salary == 2_000_000
    assert india.median_salary == 2_000_000
    assert india.average_salary_usd == 24_000
    assert us.median_salary == 120_000  # even count -> mean of middle two


def test_job_title_stats_within_a_country(insights):
    stats = {s.job_title: s for s in insights.job_title_stats("India")}

    engineer = stats["Software Engineer"]
    assert (engineer.headcount, engineer.min_salary, engineer.max_salary) == (
        2,
        1_000_000,
        3_000_000,
    )
    assert engineer.average_salary == 2_000_000
    assert engineer.currency == "INR"
    assert stats["Data Analyst"].headcount == 1


def test_job_title_stats_reject_unknown_country(insights):
    with pytest.raises(UnsupportedCountryError):
        insights.job_title_stats("Atlantis")


def test_department_stats_across_org_are_in_usd(insights):
    stats = {s.department: s for s in insights.department_stats()}

    # Engineering: 1,000,000 + 3,000,000 INR (=48,000 USD) + 150,000 USD
    assert stats["Engineering"].headcount == 3
    assert stats["Engineering"].total_payroll_usd == 198_000
    assert stats["Engineering"].average_salary_usd == 66_000


def test_department_stats_can_be_scoped_to_a_country(insights):
    stats = insights.department_stats(country="United States")
    assert {s.department: s.headcount for s in stats} == {"Engineering": 1, "Finance": 1}
