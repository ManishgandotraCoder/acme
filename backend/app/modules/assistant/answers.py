"""Render answers from database results. Templated on purpose: numbers never come from the LLM."""

from collections.abc import Callable

from app.modules.assistant.schemas import QueryIntent
from app.modules.insights.service import InsightsService

Answer = tuple[str, list[dict]]

HELP = (
    "Sorry, I couldn't map that question to the salary data. Try e.g. "
    '"average salary of Software Engineers in India", "pay statistics for Germany" or '
    '"which department has the highest average pay?".'
)


class AnswerComposer:
    def __init__(self, insights: InsightsService, countries: list[str]) -> None:
        self._insights = insights
        self._countries = countries
        self._handlers: dict[str, Callable[[QueryIntent], Answer]] = {
            "org_summary": self._org_summary,
            "country_stats": self._country_stats,
            "job_title_stats": self._job_title_stats,
            "department_stats": self._department_stats,
        }

    def compose(self, intent: QueryIntent) -> Answer:
        handler = self._handlers.get(intent.metric)
        return handler(intent) if handler else (HELP, [])

    def _org_summary(self, _: QueryIntent) -> Answer:
        s = self._insights.summary()
        answer = (
            f"ACME has {_count(s.headcount, 'employee')} across "
            f"{_count(s.country_count, 'country', 'countries')}, with a total annual payroll of "
            f"USD {s.total_payroll_usd:,} (average USD {s.average_salary_usd:,})."
        )
        return answer, [s.model_dump()]

    def _country_stats(self, intent: QueryIntent) -> Answer:
        stats = self._insights.country_stats()
        if not intent.country:
            ranked = sorted(stats, key=lambda s: s.average_salary_usd, reverse=True)
            answer = _listing(
                "Average salary by country (USD)",
                (f"{s.country} {s.average_salary_usd:,}" for s in ranked),
            )
            return answer, [s.model_dump() for s in stats]

        stats = [s for s in stats if s.country == intent.country]
        if not stats:
            return f"There are no employees in {intent.country}.", []
        s, c = stats[0], stats[0].currency
        answer = (
            f"{s.country}: {_count(s.headcount, 'employee')}, average {c} "
            f"{s.average_salary:,} (median {c} {s.median_salary:,}, min {c} "
            f"{s.min_salary:,}, max {c} {s.max_salary:,}) ≈ USD {s.average_salary_usd:,}."
        )
        return answer, [s.model_dump()]

    def _job_title_stats(self, intent: QueryIntent) -> Answer:
        countries = [intent.country] if intent.country else self._countries
        rows = [
            {"country": country, **s.model_dump()}
            for country in countries
            for s in self._insights.job_title_stats(country)
            if intent.job_title in (None, s.job_title)
        ]
        if not rows:
            return HELP, []

        if intent.job_title and intent.country:
            r, c = rows[0], rows[0]["currency"]
            answer = (
                f"{r['job_title']} in {r['country']}: {_count(r['headcount'], 'employee')}, "
                f"average {c} {r['average_salary']:,} (min {c} {r['min_salary']:,}, "
                f"max {c} {r['max_salary']:,})."
            )
        elif intent.job_title:
            answer = _listing(
                f"Average {intent.job_title} salary by country",
                (f"{r['country']} {r['currency']} {r['average_salary']:,}" for r in rows),
            )
        else:
            answer = _listing(
                f"Average salary by job title in {intent.country}",
                (f"{r['job_title']} {r['currency']} {r['average_salary']:,}" for r in rows),
            )
        return answer, rows

    def _department_stats(self, intent: QueryIntent) -> Answer:
        stats = self._insights.department_stats(country=intent.country)
        scope = f" in {intent.country}" if intent.country else ""
        if not intent.department:
            ranked = sorted(stats, key=lambda s: s.average_salary_usd, reverse=True)
            answer = _listing(
                f"Average salary by department{scope} (USD)",
                (f"{s.department} {s.average_salary_usd:,}" for s in ranked),
            )
            return answer, [s.model_dump() for s in stats]

        stats = [s for s in stats if s.department == intent.department]
        if not stats:
            return f"There are no {intent.department} employees{scope}.", []
        s = stats[0]
        answer = (
            f"{s.department}{scope}: {_count(s.headcount, 'employee')}, average USD "
            f"{s.average_salary_usd:,} (total payroll USD {s.total_payroll_usd:,})."
        )
        return answer, [s.model_dump()]


def _listing(title: str, items) -> str:
    return f"{title}: " + "; ".join(items) + "."


def _count(n: int, singular: str, plural: str | None = None) -> str:
    return f"{n:,} {singular if n == 1 else plural or singular + 's'}"
