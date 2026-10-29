"""Read-only pay analytics.

Aggregation happens in SQL (count/min/max/avg/sum/median grouped by the relevant columns),
served by indexes. Values are converted to USD *after* grouping by country, or read from the
stored USD equivalent, so mixed currencies are never summed. Peer comparisons (outliers) stay in
local currency: peers share a country. Postgres returns averages as Decimal; they are converted
to float at this boundary before any maths.
"""

from collections import defaultdict
from datetime import date

from sqlalchemy import ColumnElement, Select, and_, case, func, select
from sqlalchemy.orm import Session

from app.modules.employees.models import Employee, SalaryChange
from app.modules.insights.schemas import (
    AboveAverageReport,
    CountryStats,
    DepartmentAboveAverage,
    DepartmentStats,
    EmployeeAboveAverage,
    JobTitleStats,
    LevelStats,
    MonthlyTrend,
    OrgSummary,
    PayOutlier,
    SalaryBand,
    SalaryTrend,
)
from app.shared.countries import FX_RATES_AS_OF, currency_for, get_country, to_usd
from app.shared.levels import level_rank

# Annual salary bands in USD: (lower bound inclusive, upper bound exclusive or None).
SALARY_BANDS: tuple[tuple[int, int | None], ...] = (
    (0, 50_000),
    (50_000, 100_000),
    (100_000, 150_000),
    (150_000, 200_000),
    (200_000, None),
)


def _median_usd():
    return func.percentile_cont(0.5).within_group(Employee.annual_salary_usd)


def _scope(stmt: Select, *, country=None, department=None, job_title=None) -> Select:
    if country:
        get_country(country)
        stmt = stmt.where(Employee.country == country)
    if department:
        stmt = stmt.where(Employee.department == department)
    if job_title:
        stmt = stmt.where(Employee.job_title == job_title)
    return stmt


class InsightsService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Overview, countries, roles, departments ----------------------------------------------

    def summary(self) -> OrgSummary:
        rows = self._session.execute(
            select(Employee.country, func.count(), func.sum(Employee.annual_salary)).group_by(
                Employee.country
            )
        ).all()
        median = self._session.scalar(select(_median_usd()))
        headcount = sum(count for _, count, _ in rows)
        total_usd = sum(to_usd(total, country) for country, _, total in rows)
        return OrgSummary(
            headcount=headcount,
            country_count=len(rows),
            total_payroll_usd=total_usd,
            average_salary_usd=round(total_usd / headcount) if headcount else 0,
            median_salary_usd=round(median or 0),
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
                func.percentile_cont(0.5).within_group(Employee.annual_salary),
            )
            .group_by(Employee.country)
            .order_by(Employee.country)
        ).all()

        return [
            CountryStats(
                country=country,
                currency=currency_for(country),
                headcount=count,
                min_salary=lo,
                max_salary=hi,
                average_salary=round(avg),
                median_salary=round(median),
                average_salary_usd=to_usd(float(avg), country),
                median_salary_usd=to_usd(median, country),
            )
            for country, count, lo, hi, avg, median in aggregates
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
        stmt = _scope(
            select(
                Employee.department,
                Employee.country,
                func.count(),
                func.sum(Employee.annual_salary),
            ).group_by(Employee.department, Employee.country),
            country=country,
        )
        headcount: dict[str, int] = defaultdict(int)
        total_usd: dict[str, int] = defaultdict(int)
        for department, row_country, count, total in self._session.execute(stmt):
            headcount[department] += count
            total_usd[department] += to_usd(total, row_country)

        medians = dict(
            self._session.execute(
                _scope(
                    select(Employee.department, _median_usd()).group_by(Employee.department),
                    country=country,
                )
            ).all()
        )
        return [
            DepartmentStats(
                department=department,
                headcount=headcount[department],
                total_payroll_usd=total_usd[department],
                average_salary_usd=round(total_usd[department] / headcount[department]),
                median_salary_usd=round(medians[department]),
            )
            for department in sorted(headcount)
        ]

    # --- Pay equity --------------------------------------------------------------------------

    def level_stats(
        self,
        *,
        job_title: str | None = None,
        department: str | None = None,
        country: str | None = None,
    ) -> list[LevelStats]:
        """Pay per job level, lowest first, with the gap between consecutive medians."""
        rows = self._session.execute(
            _scope(
                select(
                    Employee.job_level,
                    func.count(),
                    func.avg(Employee.annual_salary_usd),
                    _median_usd(),
                ).group_by(Employee.job_level),
                country=country,
                department=department,
                job_title=job_title,
            )
        ).all()

        stats: list[LevelStats] = []
        for level, count, avg, median in sorted(rows, key=lambda r: level_rank(r[0])):
            previous = stats[-1].median_salary_usd if stats else None
            stats.append(
                LevelStats(
                    job_level=level,
                    headcount=count,
                    average_salary_usd=round(avg),
                    median_salary_usd=round(median),
                    gap_to_previous_pct=round((median - previous) / previous * 100, 1)
                    if previous
                    else None,
                )
            )
        return stats

    def outliers(
        self,
        *,
        threshold_pct: float = 25,
        min_peers: int = 5,
        limit: int = 20,
        department: str | None = None,
        country: str | None = None,
    ) -> list[PayOutlier]:
        """Employees paid at least ``threshold_pct`` above or below the median of their peers:
        same job title, level and country (so local currency, no FX). Peer groups smaller than
        ``min_peers`` are skipped; their median says little."""
        peer_key = (Employee.job_title, Employee.job_level, Employee.country)
        peers = (
            select(
                *peer_key,
                func.percentile_cont(0.5).within_group(Employee.annual_salary).label("median"),
                func.count().label("size"),
            )
            .group_by(*peer_key)
            .having(func.count() >= min_peers)
            .subquery()
        )
        deviation = (Employee.annual_salary - peers.c.median) / peers.c.median
        stmt = _scope(
            select(Employee, peers.c.median, peers.c.size, deviation)
            .join(
                peers,
                and_(*(column == peers.c[column.key] for column in peer_key)),
            )
            .where(func.abs(deviation) >= threshold_pct / 100)
            .order_by(func.abs(deviation).desc(), Employee.id)
            .limit(limit),
            department=department,
            country=country,
        )
        return [
            PayOutlier(
                employee_id=e.id,
                full_name=e.full_name,
                job_title=e.job_title,
                job_level=e.job_level,
                department=e.department,
                country=e.country,
                currency=e.currency,
                annual_salary=e.annual_salary,
                peer_median_salary=round(median),
                peer_count=size,
                deviation_pct=round(dev * 100, 1),
            )
            for e, median, size, dev in self._session.execute(stmt)
        ]

    def above_department_average(self, *, limit: int = 10) -> AboveAverageReport:
        """Who earns more than their department's average, in USD terms (departments span
        countries, so only the USD equivalent is comparable)."""
        averages = (
            select(
                Employee.department,
                func.avg(Employee.annual_salary_usd).label("average"),
                func.count().label("headcount"),
            )
            .group_by(Employee.department)
            .subquery()
        )
        is_above: ColumnElement[bool] = Employee.annual_salary_usd > averages.c.average
        joined = select().join_from(
            Employee, averages, Employee.department == averages.c.department
        )

        per_department = self._session.execute(
            joined.add_columns(
                Employee.department,
                averages.c.average,
                averages.c.headcount,
                func.count().filter(is_above),
            )
            .group_by(Employee.department, averages.c.average, averages.c.headcount)
            .order_by(Employee.department)
        ).all()
        margin = Employee.annual_salary_usd - averages.c.average
        top = self._session.execute(
            joined.add_columns(Employee, averages.c.average, margin)
            .where(is_above)
            .order_by(margin.desc(), Employee.id)
            .limit(limit)
        ).all()

        return AboveAverageReport(
            headcount=sum(r[2] for r in per_department),
            employees_above=sum(r[3] for r in per_department),
            departments=[
                DepartmentAboveAverage(
                    department=department,
                    headcount=headcount,
                    above=above,
                    average_salary_usd=round(average),
                )
                for department, average, headcount, above in per_department
            ],
            top=[
                EmployeeAboveAverage(
                    employee_id=e.id,
                    full_name=e.full_name,
                    job_title=e.job_title,
                    department=e.department,
                    country=e.country,
                    annual_salary_usd=e.annual_salary_usd,
                    department_average_usd=round(average),
                    above_by_usd=round(above_by),
                )
                for e, average, above_by in top
            ],
        )

    # --- Distribution and trends -------------------------------------------------------------

    def salary_bands(
        self, *, department: str | None = None, country: str | None = None
    ) -> list[SalaryBand]:
        band = case(
            *(
                (Employee.annual_salary_usd < upper, index)
                for index, (_, upper) in enumerate(SALARY_BANDS)
                if upper is not None
            ),
            else_=len(SALARY_BANDS) - 1,
        )
        counts = dict(
            self._session.execute(
                _scope(
                    select(band, func.count()).group_by(band),
                    department=department,
                    country=country,
                )
            ).all()
        )
        return [
            SalaryBand(
                label=_band_label(lower, upper),
                min_usd=lower,
                max_usd=upper,
                headcount=counts.get(index, 0),
            )
            for index, (lower, upper) in enumerate(SALARY_BANDS)
        ]

    def salary_trends(
        self,
        *,
        as_of: date | None = None,
        months: int = 12,
        department: str | None = None,
        country: str | None = None,
    ) -> SalaryTrend:
        """Salary changes by effective month over the last ``months`` months up to ``as_of``."""
        end = as_of or date.today()
        month_starts = _month_starts(end, months)
        stmt = select(SalaryChange).where(SalaryChange.effective_date.between(month_starts[0], end))
        if department or country:
            stmt = _scope(
                stmt.join(Employee, Employee.id == SalaryChange.employee_id),
                department=department,
                country=country,
            )
        window = stmt.subquery()
        month = func.to_char(window.c.effective_date, "YYYY-MM")
        raise_pct = _raise_pct(window)

        by_month = {
            key: (count, average)
            for key, count, average in self._session.execute(
                select(month, func.count(), func.avg(raise_pct)).group_by(month)
            )
        }
        changes, employees, average = self._session.execute(
            select(func.count(), func.count(window.c.employee_id.distinct()), func.avg(raise_pct))
        ).one()

        return SalaryTrend(
            start=month_starts[0].isoformat(),
            end=end.isoformat(),
            changes=changes,
            employees=employees,
            average_raise_pct=_pct(average),
            months=[
                MonthlyTrend(
                    month=key,
                    changes=by_month.get(key, (0, None))[0],
                    average_raise_pct=_pct(by_month.get(key, (0, None))[1]),
                )
                for key in (m.strftime("%Y-%m") for m in month_starts)
            ],
        )


def _raise_pct(window):
    """Raise in percent for a change that kept its currency; NULL otherwise (ignored by AVG)."""
    return case(
        (
            window.c.previous_currency == window.c.new_currency,
            (window.c.new_salary - window.c.previous_salary) * 100.0 / window.c.previous_salary,
        )
    )


def _pct(value) -> float | None:
    return None if value is None else round(float(value), 1)


def _month_starts(end: date, months: int) -> list[date]:
    first = end.replace(day=1)
    starts = []
    for back in range(months - 1, -1, -1):
        year, month = divmod(first.year * 12 + first.month - 1 - back, 12)
        starts.append(date(year, month + 1, 1))
    return starts


def _band_label(lower: int, upper: int | None) -> str:
    if lower == 0:
        return f"Under USD {upper // 1000}k"
    if upper is None:
        return f"USD {lower // 1000}k+"
    return f"USD {lower // 1000}k–{upper // 1000}k"
