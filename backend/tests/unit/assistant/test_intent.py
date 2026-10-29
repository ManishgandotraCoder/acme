"""Pure tests for intent resolution: no database, no LLM — just the grounding rules."""

import pytest

from app.modules.assistant.intent import IntentResolver, Vocabulary
from app.modules.assistant.schemas import QueryIntent

VOCAB = Vocabulary(
    countries=["Germany", "India", "United Kingdom", "United States"],
    job_titles=["Data Analyst", "Senior Software Engineer", "Software Engineer"],
    departments=["Data", "Engineering", "Finance", "Sales"],
)
resolve = IntentResolver(VOCAB).resolve


def test_entities_come_from_the_question_even_if_the_model_omits_them():
    intent = resolve({"metric": "job_title_stats"}, "data analysts in Germany")
    assert intent == QueryIntent(
        metric="job_title_stats", countries=["Germany"], job_titles=["Data Analyst"]
    )


def test_a_department_is_not_read_from_inside_a_job_title():
    # "data analysts" names a role; it does not also mean the Data department.
    assert resolve({"metric": "job_title_stats"}, "data analysts pay").departments == []


def test_every_mentioned_value_is_kept_for_comparisons():
    intent = resolve({"metric": "department_stats"}, "Compare Engineering and Sales salaries")
    assert intent.departments == ["Engineering", "Sales"]


def test_model_values_not_grounded_in_the_question_are_dropped():
    raw = {"metric": "department_stats", "departments": ["Finance"]}
    assert resolve(raw, "which pays most?").departments == []


def test_model_values_that_are_unknown_are_dropped():
    raw = {"metric": "job_title_stats", "departments": ["IT/Software"]}
    assert resolve(raw, "software pay").departments == []


def test_partially_mentioned_model_value_is_kept_with_known_spelling():
    raw = {"metric": "job_title_stats", "job_titles": ["data analyst"]}
    assert resolve(raw, "what do analysts earn?").job_titles == ["Data Analyst"]


@pytest.mark.parametrize(
    ("question", "countries"),
    [
        ("pay in the US", ["United States"]),
        ("UK pay", ["United Kingdom"]),
        ("salaries in America", ["United States"]),
        ("what do we pay us?", []),  # lowercase pronoun is not a country
        ("India vs the UK", ["India", "United Kingdom"]),
    ],
)
def test_country_abbreviations_and_aliases(question, countries):
    assert resolve({"metric": "country_stats"}, question).countries == countries


@pytest.mark.parametrize(
    ("question", "statistic"),
    [
        ("Which department has the highest median salary?", "median"),
        ("Which department pays most?", "average"),
    ],
)
def test_statistic_is_read_from_the_question(question, statistic):
    # The model's choice is ignored: the word in the question decides.
    raw = {
        "metric": "department_stats",
        "statistic": "average" if statistic == "median" else "median",
    }
    assert resolve(raw, question).statistic == statistic


@pytest.mark.parametrize(
    "metric",
    ["level_stats", "salary_bands", "outliers", "above_department_average", "salary_trends"],
)
def test_analytics_operations_are_allowed(metric):
    assert resolve({"metric": metric}, "q").metric == metric


@pytest.mark.parametrize("raw", [{}, {"metric": "drop_tables"}, {"metric": "unsupported"}])
def test_invalid_or_declined_output_is_unsupported(raw):
    assert resolve(raw, "anything").metric == "unsupported"
