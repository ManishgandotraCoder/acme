"""Turn the model's raw output into a trustworthy ``QueryIntent``.

Trust the model for *what* is asked (the metric), but verify *which* entities against the
question text. Small models drop entities the user named and invent filters the user never
asked for (see docs/AI_USAGE.md), so:

1. an entity named in the question (plural-tolerant, longest match) always wins;
2. otherwise a model-supplied value is kept only if it is a known value AND shares a word
   with the question.
"""

import difflib
import re
from dataclasses import dataclass

from pydantic import ValidationError

from app.modules.assistant.schemas import ModelIntent, QueryIntent

UNSUPPORTED = QueryIntent(metric="unsupported")

# Case-sensitive so the pronoun "us" is not read as a country.
_COUNTRY_ABBREVIATIONS = {"US": "United States", "USA": "United States", "UK": "United Kingdom"}
_COUNTRY_ALIASES = {
    "america": "United States",
    "britain": "United Kingdom",
    "england": "United Kingdom",
}


@dataclass(frozen=True, slots=True)
class Vocabulary:
    """Known values the question may refer to."""

    countries: list[str]
    job_titles: list[str]
    departments: list[str]


class IntentResolver:
    def __init__(self, vocabulary: Vocabulary) -> None:
        self._vocab = vocabulary

    def resolve(self, raw: dict, question: str) -> QueryIntent:
        try:
            parsed = ModelIntent.model_validate(raw)
        except ValidationError:
            return UNSUPPORTED
        if parsed.metric == "unsupported":
            return UNSUPPORTED

        v = self._vocab
        return QueryIntent(
            metric=parsed.metric,
            country=_mentioned_country(question, v.countries)
            or _grounded(parsed.country, v.countries, question),
            job_title=_mentioned(question, v.job_titles)
            or _grounded(parsed.job_title, v.job_titles, question),
            department=_mentioned(question, v.departments)
            or _grounded(parsed.department, v.departments, question),
        )


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
