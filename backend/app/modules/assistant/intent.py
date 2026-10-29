"""Turn the model's raw output into a trustworthy ``QueryIntent``.

Trust the model for *what* is asked (the analytics operation), but verify *which* entities
against the question text. Small models drop entities the user named and invent filters the user
never asked for (see docs/AI_USAGE.md), so:

1. values named in the question (plural-tolerant, longest match first) always win; a span of
   text names at most one value, so "data analysts" is a role, not also the Data department;
2. otherwise a model-supplied value is kept only if it is a known value AND shares a word
   with the question;
3. "median" vs "average" is read from the question, never from the model.
"""

import difflib
import re
from dataclasses import dataclass

from pydantic import ValidationError

from app.modules.assistant.schemas import ParsedIntent, QueryIntent

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
            parsed = ParsedIntent.model_validate(raw)
        except ValidationError:
            return UNSUPPORTED
        if parsed.metric == "unsupported":
            return UNSUPPORTED

        v = self._vocab
        text = _Text(question)
        # Most specific kind first: job titles contain department and country-like words.
        mentioned_titles = _values(text.take(v.job_titles))
        mentioned_departments = _values(text.take(v.departments))
        mentioned_countries = _values(text.take(v.countries) + text.take_country_aliases())
        # Model guesses must be grounded in words no explicit mention already accounts for:
        # "salary in Engineering" names the department, not the Engineering Manager role.
        rest = text.remaining
        job_titles = mentioned_titles or _grounded(parsed.job_titles, v.job_titles, rest)
        departments = mentioned_departments or _grounded(parsed.departments, v.departments, rest)
        countries = mentioned_countries or _grounded(parsed.countries, v.countries, rest)

        metric = parsed.metric
        if metric == "job_title_stats" and departments and not job_titles:
            metric = "department_stats"  # a "role" question that only names departments
        return QueryIntent(
            metric=metric,
            job_titles=job_titles,
            departments=departments,
            countries=countries,
            statistic="median" if re.search(r"\bmedian\b", question, re.I) else "average",
        )


class _Text:
    """The question, with matched spans blanked out so no text names two values."""

    def __init__(self, question: str) -> None:
        self.original = question
        self._folded = question.casefold()

    def take(self, candidates: list[str]) -> list[tuple[int, str]]:
        """Known values named in the text, longest first, with where they were found."""
        found = []
        for candidate in sorted(candidates, key=len, reverse=True):
            pattern = rf"\b{re.escape(candidate.casefold())}(?:s|es)?\b"
            if match := re.search(pattern, self._folded):
                found.append((match.start(), candidate))
                self._blank(match)
        return found

    def take_country_aliases(self) -> list[tuple[int, str]]:
        found = []
        for abbreviation, country in _COUNTRY_ABBREVIATIONS.items():
            if match := re.search(rf"\b{abbreviation}\b", self.original):
                found.append((match.start(), country))
                self._blank(match)
        for alias, country in _COUNTRY_ALIASES.items():
            if match := re.search(rf"\b{alias}\b", self._folded):
                found.append((match.start(), country))
                self._blank(match)
        return found

    @property
    def remaining(self) -> str:
        """The text not yet claimed by a mention."""
        return self._folded

    def _blank(self, match: re.Match) -> None:
        start, end = match.span()
        self._folded = self._folded[:start] + " " * (end - start) + self._folded[end:]


def _values(found: list[tuple[int, str]]) -> list[str]:
    """Values in the order the question mentions them, without repeats ("US ... America")."""
    return list(dict.fromkeys(value for _, value in sorted(found)))


def _grounded(values: list[str], candidates: list[str], question: str) -> list[str]:
    """Model-supplied values that map to a known value sharing a word with the question."""
    question_words = {_singular(w) for w in re.findall(r"[a-z]+", question.casefold())}
    kept = []
    for value in values:
        known = _closest(value, candidates)
        if known is None:
            continue
        known_words = {_singular(w) for w in re.findall(r"[a-z]+", known.casefold()) if len(w) > 2}
        if known_words & question_words and known not in kept:
            kept.append(known)
    return kept


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


def mentioned(question: str, values: list[str]) -> list[str]:
    """Which of ``values`` the question names explicitly (as opposed to a model's guess)."""
    return _values(_Text(question).take(values))


def ambiguous_roles(question: str, job_titles: list[str]) -> list[str]:
    """Job titles a vague word in the question could mean ("engineers" -> every *Engineer*)."""
    words = {_singular(w) for w in re.findall(r"[a-z]+", question.casefold()) if len(w) > 3}
    for word in sorted(words):
        matches = [t for t in job_titles if word in {_singular(x) for x in t.casefold().split()}]
        if len(matches) > 1:
            return sorted(matches)
    return []
