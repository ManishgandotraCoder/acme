import pytest

from app.ai.ask_service import AskService, QueryIntent
from app.ai.llm import LLMUnavailableError
from tests.conftest import build_employee


class FakeLLM:
    """Returns a canned intent and records what it was asked."""

    def __init__(self, response: dict | Exception) -> None:
        self._response = response
        self.calls: list[tuple[str, str]] = []

    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        self.calls.append((system, user))
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


@pytest.fixture
def seeded(session):
    session.add_all(
        [
            build_employee(
                email="a@example.com",
                country="Germany",
                currency="EUR",
                job_title="Data Analyst",
                department="Finance",
                annual_salary=60_000,
            ),
            build_employee(
                email="b@example.com",
                country="Germany",
                currency="EUR",
                job_title="Data Analyst",
                department="Finance",
                annual_salary=80_000,
            ),
            build_employee(
                email="c@example.com",
                country="India",
                currency="INR",
                job_title="Software Engineer",
                annual_salary=2_000_000,
            ),
        ]
    )
    session.commit()
    return session


def _ask(session, llm_response, question="q"):
    return AskService(session, FakeLLM(llm_response)).ask(question)


def test_prompt_grounds_the_model_in_real_countries_and_job_titles(seeded):
    llm = FakeLLM({"metric": "org_summary"})
    AskService(seeded, llm).ask("How much do we pay overall?")

    system, user = llm.calls[0]
    assert "Germany" in system and "Data Analyst" in system and "Finance" in system
    assert user == "How much do we pay overall?"


def test_answers_job_title_question_with_numbers_from_the_database(seeded):
    result = _ask(
        seeded,
        {"metric": "job_title_stats", "country": "germany", "job_title": "data analysts"},
        question="What do data analysts earn in Germany?",
    )

    assert result.intent == QueryIntent(
        metric="job_title_stats", country="Germany", job_title="Data Analyst"
    )
    assert result.answer == (
        "Data Analyst in Germany: 2 employees, average EUR 70,000 (min EUR 60,000, max EUR 80,000)."
    )


def test_answers_country_question(seeded):
    result = _ask(seeded, {"metric": "country_stats", "country": "India"}, "Pay in India?")
    assert result.answer.startswith("India: 1 employee, average INR 2,000,000")


def test_country_question_without_country_lists_all_countries(seeded):
    result = _ask(seeded, {"metric": "country_stats"})
    assert [row["country"] for row in result.data] == ["Germany", "India"]


def test_answers_org_summary(seeded):
    result = _ask(seeded, {"metric": "org_summary"})
    assert "3 employees across 2 countries" in result.answer


def test_answers_department_question(seeded):
    result = _ask(seeded, {"metric": "department_stats", "department": "finance"}, "Finance pay?")
    assert result.answer.startswith("Finance: 2 employees, average USD 75,600")


def test_unknown_job_title_is_dropped_and_answer_states_its_real_scope(seeded):
    result = _ask(
        seeded,
        {"metric": "job_title_stats", "country": "Germany", "job_title": "Wizard"},
        question="What do wizards earn in Germany?",
    )
    assert result.intent.job_title is None
    assert result.answer.startswith("Average salary by job title in Germany")


def test_model_can_decline_off_topic_questions(seeded):
    result = _ask(seeded, {"metric": "unsupported"}, "What's the weather tomorrow?")
    assert result.intent.metric == "unsupported"
    assert "couldn't" in result.answer.lower()


# --- Regression tests from running against the real llama3.2 model -------------------


def test_entities_omitted_by_the_model_are_recovered_from_the_question(seeded):
    result = _ask(
        seeded,
        {"metric": "job_title_stats", "job_title": "Data Analyst"},
        question="What is the average salary of data analysts in Germany?",
    )
    assert (result.intent.country, result.intent.job_title) == ("Germany", "Data Analyst")


def test_filters_invented_by_the_model_are_ignored(seeded):
    result = _ask(
        seeded,
        {"metric": "department_stats", "department": "Finance"},
        question="Which department has the highest average pay?",
    )
    assert result.intent.department is None
    assert result.answer.startswith("Average salary by department (USD)")


def test_unknown_values_invented_by_the_model_do_not_block_the_answer(seeded):
    result = _ask(
        seeded,
        {
            "metric": "job_title_stats",
            "job_title": "Software Engineer",
            "department": "IT/Software Development",
        },
        question="How much do we pay software engineers in India?",
    )
    assert result.intent == QueryIntent(
        metric="job_title_stats", country="India", job_title="Software Engineer"
    )


@pytest.mark.parametrize(
    ("question", "country"),
    [("Average pay in the US?", "United States"), ("UK salaries", "United Kingdom")],
)
def test_common_country_abbreviations_are_understood(seeded, question, country):
    result = _ask(seeded, {"metric": "country_stats"}, question)
    assert result.intent.country == country


def test_longest_job_title_mention_wins(session):
    session.add_all(
        [
            build_employee(email="a@example.com", job_title="Software Engineer"),
            build_employee(email="b@example.com", job_title="Senior Software Engineer"),
        ]
    )
    session.commit()
    result = _ask(session, {"metric": "job_title_stats"}, "Senior software engineer pay in the UK")
    assert result.intent.job_title == "Senior Software Engineer"


def test_malformed_llm_output_is_treated_as_unsupported(seeded):
    result = _ask(seeded, {"metric": "drop_tables"})
    assert result.intent.metric == "unsupported"


def test_llm_outage_propagates_as_unavailable(seeded):
    with pytest.raises(LLMUnavailableError):
        _ask(seeded, LLMUnavailableError("down"))
