"""Answer plain-English pay questions.

The LLM is used *only* to classify a question into a whitelisted ``QueryIntent``. All
numbers come from ``InsightsService`` and the answer text is rendered from templates, so
the model can never invent a salary figure or run arbitrary queries.
"""

import difflib
import re
from typing import Literal

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.ai.llm import LLMClient
from app.domain.countries import SUPPORTED_COUNTRIES
from app.repositories.employee_repository import EmployeeRepository
from app.services.insights_service import InsightsService

Metric = Literal["org_summary", "country_stats", "job_title_stats", "department_stats"]


class QueryIntent(BaseModel):
    metric: Metric | Literal["unsupported"]
    country: str | None = None
    job_title: str | None = None
    department: str | None = None


class AskResult(BaseModel):
    question: str
    answer: str
    intent: QueryIntent
    data: list[dict]


class _LLMIntent(BaseModel):
    """Shape the model must produce; also used as the JSON schema sent to Ollama."""

    metric: Metric | Literal["unsupported"]
    country: str | None = None
    job_title: str | None = None
    department: str | None = None


_SYSTEM_PROMPT = """\
You translate HR questions about employee salaries into a JSON query. Reply with JSON only.

Choose "metric":
- "org_summary": overall headcount, total payroll or average pay for the whole company.
- "country_stats": pay statistics (min/max/average/median) for a country or comparing countries.
- "job_title_stats": pay for a job title / role, optionally within a country.
- "department_stats": pay or headcount per department, optionally within a country.
- "unsupported": the question is not about employee pay or headcount.

Set "country", "job_title" and "department" ONLY when the question explicitly names one;
otherwise leave them out. Use the exact spelling from these lists:
Countries: {countries}
Job titles: {job_titles}
Departments: {departments}
"""

_UNSUPPORTED = QueryIntent(metric="unsupported")

# Case-sensitive so the pronoun "us" is not read as a country.
_COUNTRY_ABBREVIATIONS = {"US": "United States", "USA": "United States", "UK": "United Kingdom"}
_COUNTRY_ALIASES = {
    "america": "United States",
    "britain": "United Kingdom",
    "england": "United Kingdom",
}
_HELP = (
    "Sorry, I couldn't map that question to the salary data. Try e.g. "
    '"average salary of Software Engineers in India", "pay statistics for Germany" or '
    '"which department has the highest average pay?".'
)


class AskService:
    def __init__(self, session: Session, llm: LLMClient) -> None:
        self._llm = llm
        self._insights = InsightsService(session)
        repo = EmployeeRepository(session)
        self._countries = [c.name for c in SUPPORTED_COUNTRIES]
        self._job_titles = repo.distinct_job_titles()
        self._departments = repo.distinct_departments()

    def ask(self, question: str) -> AskResult:
        system = _SYSTEM_PROMPT.format(
            countries=", ".join(self._countries),
            job_titles=", ".join(self._job_titles),
            departments=", ".join(self._departments),
        )
        raw = self._llm.complete_json(system, question, _LLMIntent.model_json_schema())
        intent = self._resolve(raw, question)
        answer, data = self._execute(intent)
        return AskResult(question=question, answer=answer, intent=intent, data=data)

    # --- interpretation -----------------------------------------------------------------

    def _resolve(self, raw: dict, question: str) -> QueryIntent:
        """Trust the model for *what* is asked, but verify *which* entities against the text.

        Small models drop entities the user named and invent filters the user never asked
        for. So each entity is taken from the question itself when it names a known value;
        a model-supplied value is kept only if it is a known value grounded in the question.
        """
        try:
            parsed = _LLMIntent.model_validate(raw)
        except ValidationError:
            return _UNSUPPORTED
        if parsed.metric == "unsupported":
            return _UNSUPPORTED

        return QueryIntent(
            metric=parsed.metric,
            country=_mentioned_country(question, self._countries)
            or _grounded(parsed.country, self._countries, question),
            job_title=_mentioned(question, self._job_titles)
            or _grounded(parsed.job_title, self._job_titles, question),
            department=_mentioned(question, self._departments)
            or _grounded(parsed.department, self._departments, question),
        )

    # --- execution ----------------------------------------------------------------------

    def _execute(self, intent: QueryIntent) -> tuple[str, list[dict]]:
        handler = {
            "org_summary": self._org_summary,
            "country_stats": self._country_stats,
            "job_title_stats": self._job_title_stats,
            "department_stats": self._department_stats,
        }.get(intent.metric)
        if handler is None:
            return _HELP, []
        return handler(intent)

    def _org_summary(self, _: QueryIntent) -> tuple[str, list[dict]]:
        s = self._insights.summary()
        answer = (
            f"ACME has {_count(s.headcount, 'employee')} across "
            f"{_count(s.country_count, 'country', 'countries')}, with a total annual payroll of "
            f"USD {s.total_payroll_usd:,} (average USD {s.average_salary_usd:,})."
        )
        return answer, [s.model_dump()]

    def _country_stats(self, intent: QueryIntent) -> tuple[str, list[dict]]:
        stats = self._insights.country_stats()
        if intent.country:
            stats = [s for s in stats if s.country == intent.country]
            if not stats:
                return f"There are no employees in {intent.country}.", []
            s = stats[0]
            c = s.currency
            answer = (
                f"{s.country}: {_count(s.headcount, 'employee')}, average {c} "
                f"{s.average_salary:,} (median {c} {s.median_salary:,}, min {c} "
                f"{s.min_salary:,}, max {c} {s.max_salary:,}) ≈ USD {s.average_salary_usd:,}."
            )
        else:
            ranked = sorted(stats, key=lambda s: s.average_salary_usd, reverse=True)
            answer = (
                "Average salary by country (USD): "
                + "; ".join(f"{s.country} {s.average_salary_usd:,}" for s in ranked)
                + "."
            )
        return answer, [s.model_dump() for s in stats]

    def _job_title_stats(self, intent: QueryIntent) -> tuple[str, list[dict]]:
        countries = [intent.country] if intent.country else self._countries
        rows = [
            {"country": country, **s.model_dump()}
            for country in countries
            for s in self._insights.job_title_stats(country)
            if intent.job_title in (None, s.job_title)
        ]
        if not rows:
            return _HELP, []

        if intent.job_title and intent.country:
            r = rows[0]
            c = r["currency"]
            answer = (
                f"{r['job_title']} in {r['country']}: {_count(r['headcount'], 'employee')}, "
                f"average {c} {r['average_salary']:,} (min {c} {r['min_salary']:,}, "
                f"max {c} {r['max_salary']:,})."
            )
        elif intent.job_title:
            answer = (
                f"Average {intent.job_title} salary by country: "
                + "; ".join(f"{r['country']} {r['currency']} {r['average_salary']:,}" for r in rows)
                + "."
            )
        else:
            answer = (
                f"Average salary by job title in {intent.country}: "
                + "; ".join(
                    f"{r['job_title']} {r['currency']} {r['average_salary']:,}" for r in rows
                )
                + "."
            )
        return answer, rows

    def _department_stats(self, intent: QueryIntent) -> tuple[str, list[dict]]:
        stats = self._insights.department_stats(country=intent.country)
        scope = f" in {intent.country}" if intent.country else ""
        if intent.department:
            stats = [s for s in stats if s.department == intent.department]
            if not stats:
                return f"There are no {intent.department} employees{scope}.", []
            s = stats[0]
            answer = (
                f"{s.department}{scope}: {_count(s.headcount, 'employee')}, average USD "
                f"{s.average_salary_usd:,} (total payroll USD {s.total_payroll_usd:,})."
            )
        else:
            ranked = sorted(stats, key=lambda s: s.average_salary_usd, reverse=True)
            answer = (
                f"Average salary by department{scope} (USD): "
                + "; ".join(f"{s.department} {s.average_salary_usd:,}" for s in ranked)
                + "."
            )
        return answer, [s.model_dump() for s in stats]


def _mentioned(question: str, candidates: list[str]) -> str | None:
    """Known value named in the question (plural-tolerant); the longest match wins."""
    text = question.casefold()
    for candidate in sorted(candidates, key=len, reverse=True):
        if re.search(rf"\b{re.escape(candidate.casefold())}(?:s|es)?\b", text):
            return candidate
    return None


def _mentioned_country(question: str, countries: list[str]) -> str | None:
    if found := _mentioned(question, countries):
        return found
    for abbreviation, country in _COUNTRY_ABBREVIATIONS.items():
        if re.search(rf"\b{abbreviation}\b", question):
            return country
    alias = _mentioned(question, list(_COUNTRY_ALIASES))
    return _COUNTRY_ALIASES[alias] if alias else None


def _grounded(value: str | None, candidates: list[str], question: str) -> str | None:
    """A model-supplied value, if it maps to a known value sharing a word with the question."""
    if not value:
        return None
    known = _closest(value, candidates)
    if known is None:
        return None
    question_words = {_singular(w) for w in re.findall(r"[a-z]+", question.casefold())}
    known_words = {_singular(w) for w in re.findall(r"[a-z]+", known.casefold()) if len(w) > 2}
    return known if known_words & question_words else None


def _closest(value: str, candidates: list[str]) -> str | None:
    """Map free-text from the model onto a known value ("data analysts" -> "Data Analyst")."""
    by_key = {c.casefold(): c for c in candidates}
    key = value.strip().casefold()
    for attempt in (key, _singular(key)):
        if attempt in by_key:
            return by_key[attempt]
    close = difflib.get_close_matches(key, list(by_key), n=1, cutoff=0.8)
    return by_key[close[0]] if close else None


def _singular(word: str) -> str:
    return word.removesuffix("s") if len(word) > 3 and not word.endswith("ss") else word


def _count(n: int, singular: str, plural: str | None = None) -> str:
    return f"{n:,} {singular if n == 1 else plural or singular + 's'}"
