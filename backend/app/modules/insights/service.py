"""Read-only pay analytics.

Aggregation happens in SQL (count/min/max/avg/sum grouped by the relevant columns). Values
are converted to USD *after* grouping by country, so mixed currencies are never summed.
"""

from collections import defaultdict
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.employees.models import Employee
from app.modules.insights.schemas import CountryStats, DepartmentStats, JobTitleStats, OrgSummary
from app.shared.countries import FX_RATES_AS_OF, currency_for, get_country, to_usd


class InsightsService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def summary(self) -> OrgSummary:
        rows = self._session.execute(
            select(Employee.country, func.count(), func.sum(Employee.annual_salary)).group_by(
                Employee.country
            )
        ).all()
        headcount = sum(count for _, count, _ in rows)
        total_usd = sum(to_usd(total, country) for country, _, total in rows)
        return OrgSummary(
            headcount=headcount,
            country_count=len(rows),
            total_payroll_usd=total_usd,
            average_salary_usd=round(total_usd / headcount) if headcount else 0,
            fx_rates_as_of=FX_RATES_AS_OF,
        )

    def country_stats(self) -> list[CountryStats]:
        aggregates = self._session.execute(
            select(
                Employee.country,
                func.count(),
                func.min(Employee.annual_salary),
                func.max(Employee.annual_salary),
                func.avg(Employee.annual_salary),
            )
            .group_by(Employee.country)
            .order_by(Employee.country)
        ).all()
        salaries = self._salaries_by(Employee.country)

        return [
            CountryStats(
                country=country,
                currency=currency_for(country),
                headcount=count,
                min_salary=lo,
                max_salary=hi,
                average_salary=round(avg),
                median_salary=round(median(salaries[country])),
                average_salary_usd=to_usd(avg, country),
            )
            for country, count, lo, hi, avg in aggregates
        ]

    def job_title_stats(self, country: str) -> list[JobTitleStats]:
        currency = get_country(country).currency
        rows = self._session.execute(
            select(
                Employee.job_title,
                func.count(),
                func.min(Employee.annual_salary),
                func.max(Employee.annual_salary),
                func.avg(Employee.annual_salary),
            )
            .where(Employee.country == country)
            .group_by(Employee.job_title)
            .order_by(Employee.job_title)
        ).all()
        return [
            JobTitleStats(
                job_title=title,
                currency=currency,
                headcount=count,
                min_salary=lo,
                max_salary=hi,
                average_salary=round(avg),
            )
            for title, count, lo, hi, avg in rows
        ]

    def department_stats(self, country: str | None = None) -> list[DepartmentStats]:
        stmt = select(
            Employee.department, Employee.country, func.count(), func.sum(Employee.annual_salary)
        ).group_by(Employee.department, Employee.country)
        if country:
            get_country(country)
            stmt = stmt.where(Employee.country == country)

        headcount: dict[str, int] = defaultdict(int)
        total_usd: dict[str, int] = defaultdict(int)
        for department, row_country, count, total in self._session.execute(stmt):
            headcount[department] += count
            total_usd[department] += to_usd(total, row_country)

        return [
            DepartmentStats(
                department=department,
                headcount=headcount[department],
                total_payroll_usd=total_usd[department],
                average_salary_usd=round(total_usd[department] / headcount[department]),
            )
            for department in sorted(headcount)
        ]

    def _salaries_by(self, column) -> dict[str, list[int]]:
        grouped: dict[str, list[int]] = defaultdict(list)
        rows = self._session.execute(
            select(column, Employee.annual_salary).order_by(column, Employee.annual_salary)
        )
        for key, salary in rows:
            grouped[key].append(salary)
        return grouped
