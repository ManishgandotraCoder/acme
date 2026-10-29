"""Render answers from database results. Templated on purpose: numbers never come from the LLM.

Every answer states its scope (who is counted, which currency, the FX date) and carries the
rows behind it as a table, with a chart where a comparison is drawn. Privacy: individual-level
operations need the ``view_individual_pay`` permission, and without it, pay for groups smaller
than ``MIN_GROUP_SIZE`` is hidden, because an "average" of one person is that person's salary.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from app.core.actor import VIEW_INDIVIDUAL_PAY, Actor
from app.modules.assistant.intent import Vocabulary, ambiguous_roles, mentioned
from app.modules.assistant.schemas import AnswerKind, Chart, Column, QueryIntent, Table
from app.modules.insights.service import InsightsService
from app.shared.countries import FX_RATES_AS_OF, to_usd

MIN_GROUP_SIZE = 3
USD_BASIS = f"USD converted at fixed FX rates as of {FX_RATES_AS_OF}"

EXAMPLES = [
    "What are the average and median salaries across the organization?",
    "Which department has the highest median salary?",
    "Compare average salaries across countries",
    "What is the salary gap between job levels?",
    "How many employees fall into each salary band?",
    "How have salaries changed over the last 12 months?",
]
AGGREGATE_ALTERNATIVES = [
    "What is the salary gap between job levels?",
    "How many employees fall into each salary band?",
]
HELP = "Sorry, I couldn't map that question to the salary data. Try one of these questions."
FORBIDDEN = (
    "You don't have permission to see individual employees' pay, so I can't list people. "
    "I can answer with aggregate figures instead."
)


@dataclass
class Composed:
    kind: AnswerKind
    answer: str
    table: Table | None = None
    chart: Chart | None = None
    scope: str | None = None
    suggestions: list[str] = field(default_factory=list)


class AnswerComposer:
    def __init__(
        self,
        insights: InsightsService,
        vocabulary: Vocabulary,
        *,
        actor: Actor,
        today: Callable[[], date],
    ) -> None:
        self._insights = insights
        self._vocab = vocabulary
        self._sees_individuals = actor.can(VIEW_INDIVIDUAL_PAY)
        self._today = today
        self._handlers: dict[str, Callable[[QueryIntent, str], Composed]] = {
            "org_summary": self._org_summary,
            "country_stats": self._country_stats,
            "job_title_stats": self._job_title_stats,
            "department_stats": self._department_stats,
            "level_stats": self._level_stats,
            "salary_bands": self._salary_bands,
            "outliers": self._outliers,
            "above_department_average": self._above_department_average,
            "salary_trends": self._salary_trends,
        }

    def compose(self, intent: QueryIntent, question: str) -> Composed:
        handler = self._handlers.get(intent.metric)
        if handler is None:
            return Composed("unsupported", HELP, suggestions=EXAMPLES)
        return handler(intent, question)

    # --- Overview, countries, roles, departments -----------------------------------------------

    def _org_summary(self, _: QueryIntent, __: str) -> Composed:
        s = self._insights.summary()
        row = self._protect(
            s.model_dump(), ["total_payroll_usd", "average_salary_usd", "median_salary_usd"]
        )
        answer = (
            f"ACME has {_count(s.headcount, 'employee')} across "
            f"{_count(s.country_count, 'country', 'countries')}."
        )
        answer += (
            _HIDDEN
            if row["hidden"]
            else f" Total annual payroll is USD {s.total_payroll_usd:,}; average USD "
            f"{s.average_salary_usd:,}, median USD {s.median_salary_usd:,}."
        )
        table = Table(
            columns=[
                Column(key="headcount", label="Employees", format="number"),
                Column(key="country_count", label="Countries", format="number"),
                Column(key="total_payroll_usd", label="Total payroll", format="usd"),
                Column(key="average_salary_usd", label="Average salary", format="usd"),
                Column(key="median_salary_usd", label="Median salary", format="usd"),
            ],
            rows=[row],
        )
        return Composed("answer", answer, table, scope=f"All employees · {USD_BASIS}")

    def _country_stats(self, intent: QueryIntent, _: str) -> Composed:
        stats = [
            s.model_dump()
            for s in self._insights.country_stats()
            if not intent.countries or s.country in intent.countries
        ]
        if not stats:
            return Composed("answer", f"There are no employees in {_join(intent.countries)}.")
        rows = [self._protect(r, _COUNTRY_MONEY) for r in stats]
        table = Table(columns=_COUNTRY_COLUMNS, rows=rows)

        if len(intent.countries) == 1:
            r, c = rows[0], rows[0]["currency"]
            answer = f"{r['country']}: {_count(r['headcount'], 'employee')}"
            answer += (
                _HIDDEN
                if r["hidden"]
                else f", average {c} {r['average_salary']:,} (median {c} {r['median_salary']:,}, "
                f"min {c} {r['min_salary']:,}, max {c} {r['max_salary']:,}) ≈ USD "
                f"{r['average_salary_usd']:,}."
            )
            return Composed("answer", answer, table, scope=f"{r['country']} · {c}")

        key = f"{intent.statistic}_salary_usd"
        ranked = _ranked(rows, key)
        answer = _leader(ranked, "country", key, intent.statistic) + _listing(
            f"{intent.statistic.capitalize()} salary by country (USD)",
            (f"{r['country']} {_amount(r[key])}" for r in ranked),
        )
        return Composed(
            "answer",
            answer,
            Table(columns=_COUNTRY_COLUMNS, rows=ranked),
            Chart(x="country", y=key, label=f"{intent.statistic.capitalize()} salary (USD)"),
            scope=f"{_scope_of(countries=intent.countries)} · {USD_BASIS}",
        )

    def _job_title_stats(self, intent: QueryIntent, question: str) -> Composed:
        titles, countries = intent.job_titles, intent.countries
        # A role the question names explicitly needs no clarification; a model's guess does.
        named = mentioned(question, titles)
        if not named and (options := ambiguous_roles(question, self._vocab.job_titles)):
            return Composed(
                "clarification",
                f"Which role do you mean: {_join(options, 'or')}?",
                suggestions=[f"What do {t}s earn?" for t in options],
            )
        if not titles and not countries:
            return Composed(
                "clarification",
                "Which role or country do you mean?",
                suggestions=[f"What do {t}s earn?" for t in self._vocab.job_titles[:3]],
            )

        rows = [
            self._protect(
                {
                    "country": country,
                    "label": f"{s.job_title} · {country}",
                    **s.model_dump(),
                    "average_salary_usd": to_usd(s.average_salary, country),
                },
                ["min_salary", "max_salary", "average_salary", "average_salary_usd"],
            )
            for country in countries or self._vocab.countries
            for s in self._insights.job_title_stats(country)
            if not titles or s.job_title in titles
        ]
        scope = _scope_of(countries=countries, job_titles=titles)
        if not rows:
            return Composed("answer", f"No employees match: {scope}.", scope=scope)
        table = Table(columns=_ROLE_COLUMNS, rows=rows)

        if titles and len(rows) == 1:
            r, c = rows[0], rows[0]["currency"]
            answer = f"{r['job_title']} in {r['country']}: {_count(r['headcount'], 'employee')}" + (
                _HIDDEN
                if r["hidden"]
                else f", average {c} {r['average_salary']:,} (min {c} {r['min_salary']:,}, "
                f"max {c} {r['max_salary']:,})."
            )
            return Composed("answer", answer, table, scope=f"{scope} · {c}")

        if len(countries) == 1:
            answer = _listing(
                f"Average salary by job title in {countries[0]}",
                (f"{r['job_title']} {_local(r, 'average_salary')}" for r in rows),
            )
            chart = Chart(x="job_title", y="average_salary", label="Average salary")
            return Composed("answer", answer, table, chart, f"{scope} · {rows[0]['currency']}")

        x = "country" if len(titles) == 1 else "label"
        title = f"Average {titles[0]} salary" if len(titles) == 1 else "Average salary"
        answer = _listing(
            f"{title} by country",
            (f"{r[x]} {_local(r, 'average_salary')}" for r in rows),
        )
        chart = Chart(x=x, y="average_salary_usd", label="Average salary (USD)")
        return Composed("answer", answer, table, chart, f"{scope} · local currency; {USD_BASIS}")

    def _department_stats(self, intent: QueryIntent, _: str) -> Composed:
        country = intent.countries[0] if intent.countries else None
        rows = [
            self._protect(s.model_dump(), _DEPARTMENT_MONEY)
            for s in self._insights.department_stats(country=country)
            if not intent.departments or s.department in intent.departments
        ]
        scope = f"{_scope_of(countries=intent.countries[:1])} · {USD_BASIS}"
        place = f" in {country}" if country else ""
        if not rows:
            return Composed("answer", f"There are no {_join(intent.departments)} employees{place}.")

        if len(intent.departments) == 1:
            r = rows[0]
            answer = f"{r['department']}{place}: {_count(r['headcount'], 'employee')}" + (
                _HIDDEN
                if r["hidden"]
                else f", average USD {r['average_salary_usd']:,} (median USD "
                f"{r['median_salary_usd']:,}, total payroll USD {r['total_payroll_usd']:,})."
            )
            return Composed(
                "answer", answer, Table(columns=_DEPARTMENT_COLUMNS, rows=rows), scope=scope
            )

        key = f"{intent.statistic}_salary_usd"
        ranked = _ranked(rows, key)
        answer = _leader(ranked, "department", key, intent.statistic) + _listing(
            f"{intent.statistic.capitalize()} salary by department{place} (USD)",
            (f"{r['department']} {_amount(r[key])}" for r in ranked),
        )
        return Composed(
            "answer",
            answer,
            Table(columns=_DEPARTMENT_COLUMNS, rows=ranked),
            Chart(x="department", y=key, label=f"{intent.statistic.capitalize()} salary (USD)"),
            scope=scope,
        )

    # --- Pay equity --------------------------------------------------------------------------

    def _level_stats(self, intent: QueryIntent, _: str) -> Composed:
        filters = dict(
            job_title=_first(intent.job_titles),
            department=_first(intent.departments),
            country=_first(intent.countries),
        )
        rows = [
            self._protect(
                s.model_dump(), ["average_salary_usd", "median_salary_usd", "gap_to_previous_pct"]
            )
            for s in self._insights.level_stats(**filters)
        ]
        scope = (
            f"{_scope_of(**_as_lists(filters))} · gaps compare the same job title and country "
            f"one level apart · {USD_BASIS}"
        )
        if not rows:
            return Composed("answer", "No employees match these filters.", scope=scope)

        # Lead with the like-for-like gaps; org-wide medians also reflect the country mix of each
        # level, so on their own they can even fall from one level to the next.
        gaps = [
            (r["job_level"], f"{r['gap_to_previous_pct']:+.1f}% vs {previous['job_level']}")
            for previous, r in zip(rows, rows[1:], strict=False)
            if r["gap_to_previous_pct"] is not None
        ]
        like_for_like = "Like for like (same job title and country)"
        if not gaps:
            answer = f"{like_for_like}, no two levels can be compared in this scope."
        elif len(gaps) == 1:
            answer = f"{like_for_like}, {gaps[0][0]} is paid {gaps[0][1]}."
        else:
            answer = _listing(like_for_like, (f"{level} {gap}" for level, gap in gaps))
        answer += " " + _listing(
            "Org-wide median pay, which also reflects where each level's people work",
            (f"{r['job_level']} {_usd(r['median_salary_usd'])}" for r in rows),
        )
        return Composed(
            "answer",
            answer,
            Table(
                columns=[
                    Column(key="job_level", label="Level"),
                    Column(key="gap_to_previous_pct", label="vs level below", format="percent"),
                    Column(key="median_salary_usd", label="Median (org-wide)", format="usd"),
                    Column(key="average_salary_usd", label="Average (org-wide)", format="usd"),
                    Column(key="headcount", label="Employees", format="number"),
                ],
                rows=rows,
            ),
            Chart(x="job_level", y="gap_to_previous_pct", label="Pay vs level below (%)"),
            scope=scope,
        )

    def _outliers(self, intent: QueryIntent, _: str) -> Composed:
        if not self._sees_individuals:
            return Composed("forbidden", FORBIDDEN, suggestions=AGGREGATE_ALTERNATIVES)
        threshold, limit = 25, 20
        found = self._insights.outliers(
            threshold_pct=threshold,
            limit=limit,
            department=_first(intent.departments),
            country=_first(intent.countries),
        )
        rule = (
            f"at least {threshold}% above or below the median of their peers (same job title, "
            "level and country; peer groups of 5 or more)"
        )
        population = _scope_of(departments=intent.departments, countries=intent.countries)
        scope = f"{population} · local currency"
        if not found:
            return Composed("answer", f"No one is paid {rule}.", scope=scope)

        top = found[0]
        who = (
            f"At least {limit} employees are"
            if len(found) == limit
            else f"{_count(len(found), 'employee')} {'is' if len(found) == 1 else 'are'}"
        )
        answer = (
            f"{who} paid {rule}. Largest: {top.full_name} ({top.job_title}, {top.job_level}, "
            f"{top.country}) earns {top.currency} {top.annual_salary:,} vs a peer median of "
            f"{top.currency} {top.peer_median_salary:,} ({top.deviation_pct:+.1f}%)."
        )
        return Composed(
            "answer",
            answer,
            Table(
                columns=[
                    Column(key="full_name", label="Employee"),
                    Column(key="deviation_pct", label="vs peers", format="percent"),
                    Column(key="annual_salary", label="Salary", format="local"),
                    Column(key="peer_median_salary", label="Peer median", format="local"),
                    Column(key="job_title", label="Job title"),
                    Column(key="job_level", label="Level"),
                    Column(key="country", label="Country"),
                ],
                rows=[o.model_dump() for o in found],
            ),
            scope=scope,
        )

    def _above_department_average(self, _: QueryIntent, __: str) -> Composed:
        if not self._sees_individuals:
            return Composed("forbidden", FORBIDDEN, suggestions=AGGREGATE_ALTERNATIVES)
        report = self._insights.above_department_average()
        answer = (
            f"{report.employees_above:,} of {_count(report.headcount, 'employee')} earn above "
            "their department's average (in USD terms). "
            + _listing(
                "By department",
                (f"{d.department} {d.above:,} of {d.headcount:,}" for d in report.departments),
            )
        )
        if report.top:
            t = report.top[0]
            answer += (
                f" Furthest above: {t.full_name} ({t.job_title}, {t.department}, {t.country}), "
                f"USD {t.above_by_usd:,} above the USD {t.department_average_usd:,} average."
            )
        return Composed(
            "answer",
            answer,
            Table(
                columns=[
                    Column(key="full_name", label="Employee"),
                    Column(key="above_by_usd", label="Above average by", format="usd"),
                    Column(key="annual_salary_usd", label="Salary", format="usd"),
                    Column(key="department_average_usd", label="Department average", format="usd"),
                    Column(key="department", label="Department"),
                    Column(key="job_title", label="Job title"),
                    Column(key="country", label="Country"),
                ],
                rows=[t.model_dump() for t in report.top],
            ),
            scope=f"All employees · departments span countries, so pay is compared in "
            f"{USD_BASIS} · top {len(report.top)} shown",
        )

    # --- Distribution and trends -------------------------------------------------------------

    def _salary_bands(self, intent: QueryIntent, _: str) -> Composed:
        bands = self._insights.salary_bands(
            department=_first(intent.departments), country=_first(intent.countries)
        )
        return Composed(
            "answer",
            _listing(
                "Employees by annual salary (USD)", (f"{b.label}: {b.headcount:,}" for b in bands)
            ),
            Table(
                columns=[
                    Column(key="label", label="Salary band"),
                    Column(key="headcount", label="Employees", format="number"),
                ],
                rows=[b.model_dump() for b in bands],
            ),
            Chart(x="label", y="headcount", label="Employees"),
            scope=f"{_scope_of(departments=intent.departments[:1], countries=intent.countries[:1])}"
            f" · {USD_BASIS}",
        )

    def _salary_trends(self, intent: QueryIntent, _: str) -> Composed:
        trend = self._insights.salary_trends(
            as_of=self._today(),
            department=_first(intent.departments),
            country=_first(intent.countries),
        )
        hide = not self._sees_individuals
        months = [
            {
                **m.model_dump(),
                "average_raise_pct": None
                if hide and m.changes < MIN_GROUP_SIZE
                else m.average_raise_pct,
            }
            for m in trend.months
        ]
        period = f"{_month(trend.start)} – {_month(trend.end)}"
        if trend.changes == 0:
            answer = f"Over the last 12 months ({period}) there were no salary changes."
        else:
            changes = _count(trend.changes, "salary change")
            answer = (
                f"Over the last 12 months ({period}): {changes} for "
                f"{_count(trend.employees, 'employee')}"
            )
            if hide and trend.employees < MIN_GROUP_SIZE:
                answer += "; the average raise is hidden for fewer than 3 people."
            else:
                answer += f", average raise {trend.average_raise_pct:.1f}%."
            busiest = max(months, key=lambda m: m["changes"])
            answer += (
                f" Busiest month: {_month(busiest['month'])} ({busiest['changes']:,} changes)."
            )
        return Composed(
            "answer",
            answer,
            Table(
                columns=[
                    Column(key="month", label="Month"),
                    Column(key="changes", label="Salary changes", format="number"),
                    Column(key="average_raise_pct", label="Average raise", format="percent"),
                ],
                rows=months,
            ),
            Chart(x="month", y="changes", label="Salary changes"),
            scope=f"{_scope_of(departments=intent.departments[:1], countries=intent.countries[:1])}"
            " · by effective date · raises exclude currency changes",
        )

    # --- Privacy -------------------------------------------------------------------------------

    def _protect(self, row: dict, money: list[str]) -> dict:
        """Hide pay for groups too small to be anonymous, unless the actor may see individuals."""
        hidden = (
            not self._sees_individuals and row.get("headcount", MIN_GROUP_SIZE) < MIN_GROUP_SIZE
        )
        return {**row, **dict.fromkeys(money if hidden else [], None), "hidden": hidden}


_HIDDEN = " (pay figures are hidden for groups of fewer than 3 people)."

_COUNTRY_MONEY = [
    "min_salary",
    "max_salary",
    "average_salary",
    "median_salary",
    "average_salary_usd",
    "median_salary_usd",
]
_COUNTRY_COLUMNS = [
    Column(key="country", label="Country"),
    Column(key="headcount", label="Employees", format="number"),
    Column(key="average_salary", label="Average (local)", format="local"),
    Column(key="median_salary", label="Median (local)", format="local"),
    Column(key="average_salary_usd", label="Average (USD)", format="usd"),
    Column(key="median_salary_usd", label="Median (USD)", format="usd"),
]
_ROLE_COLUMNS = [
    Column(key="job_title", label="Job title"),
    Column(key="country", label="Country"),
    Column(key="headcount", label="Employees", format="number"),
    Column(key="average_salary", label="Average (local)", format="local"),
    Column(key="min_salary", label="Min (local)", format="local"),
    Column(key="max_salary", label="Max (local)", format="local"),
    Column(key="average_salary_usd", label="Average (USD)", format="usd"),
]
_DEPARTMENT_MONEY = ["total_payroll_usd", "average_salary_usd", "median_salary_usd"]
_DEPARTMENT_COLUMNS = [
    Column(key="department", label="Department"),
    Column(key="headcount", label="Employees", format="number"),
    Column(key="average_salary_usd", label="Average salary", format="usd"),
    Column(key="median_salary_usd", label="Median salary", format="usd"),
    Column(key="total_payroll_usd", label="Total payroll", format="usd"),
]


def _ranked(rows: list[dict], key: str) -> list[dict]:
    """Highest first; hidden (None) values last."""
    return sorted(rows, key=lambda r: (r[key] is None, -(r[key] or 0)))


def _leader(ranked: list[dict], name_key: str, value_key: str, statistic: str) -> str:
    top = ranked[0]
    if top[value_key] is None:
        return ""
    return f"{top[name_key]} has the highest {statistic} salary (USD {top[value_key]:,}). "


def _amount(value: int | None) -> str:
    return "hidden" if value is None else f"{value:,}"


def _usd(value: int | None) -> str:
    return "hidden" if value is None else f"USD {value:,}"


def _local(row: dict, key: str) -> str:
    return "hidden" if row[key] is None else f"{row['currency']} {row[key]:,}"


def _first(values: list[str]) -> str | None:
    return values[0] if values else None


def _as_lists(filters: dict) -> dict:
    keys = {"job_title": "job_titles", "department": "departments", "country": "countries"}
    return {keys[k]: [v] if v else [] for k, v in filters.items()}


def _scope_of(
    *, countries: list[str] = (), departments: list[str] = (), job_titles: list[str] = ()
) -> str:
    parts = [_join(v) for v in (job_titles, departments, countries) if v]
    return " · ".join(parts) if parts else "All employees"


def _join(values: list[str], last: str = "and") -> str:
    values = list(values)
    return values[0] if len(values) == 1 else f"{', '.join(values[:-1])} {last} {values[-1]}"


def _listing(title: str, items) -> str:
    return f"{title}: " + "; ".join(items) + "."


def _count(n: int, singular: str, plural: str | None = None) -> str:
    return f"{n:,} {singular if n == 1 else plural or singular + 's'}"


def _month(iso: str) -> str:
    """'2026-03' or '2026-03-01' -> 'Mar 2026'."""
    year, month = int(iso[:4]), int(iso[5:7])
    return date(year, month, 1).strftime("%b %Y")
