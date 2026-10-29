"""Pure tests for intent resolution: no database, no LLM — just the grounding rules."""

import pytest

from app.modules.assistant.intent import IntentResolver, Vocabulary
from app.modules.assistant.schemas import QueryIntent

VOCAB = Vocabulary(
    countries=["Germany", "India", "United Kingdom", "United States"],
    job_titles=["Data Analyst", "Senior Software Engineer", "Software Engineer"],
    departments=["Data", "Engineering", "Finance"],
)
resolve = IntentResolver(VOCAB).resolve


def test_entities_come_from_the_question_even_if_the_model_omits_them():
    intent = resolve({"metric": "job_title_stats"}, "data analysts in Germany")
    assert intent == QueryIntent(
        metric="job_title_stats", country="Germany", job_title="Data Analyst", department="Data"
    )


def test_model_values_not_grounded_in_the_question_are_dropped():
    intent = resolve({"metric": "department_stats", "department": "Finance"}, "which pays most?")
    assert intent.department is None


def test_model_values_that_are_unknown_are_dropped():
    intent = resolve({"metric": "job_title_stats", "department": "IT/Software"}, "software pay")
    assert intent.department is None


def test_partially_mentioned_model_value_is_kept_with_known_spelling():
    intent = resolve(
        {"metric": "job_title_stats", "job_title": "data analyst"}, "what do analysts earn?"
    )
    assert intent.job_title == "Data Analyst"


@pytest.mark.parametrize(
    ("question", "country"),
    [
        ("pay in the US", "United States"),
        ("UK pay", "United Kingdom"),
        ("salaries in America", "United States"),
        ("what do we pay us?", None),  # lowercase pronoun is not a country
    ],
)
def test_country_abbreviations_and_aliases(question, country):
    assert resolve({"metric": "country_stats"}, question).country == country


@pytest.mark.parametrize("raw", [{}, {"metric": "drop_tables"}, {"metric": "unsupported"}])
def test_invalid_or_declined_output_is_unsupported(raw):
    assert resolve(raw, "anything").metric == "unsupported"
