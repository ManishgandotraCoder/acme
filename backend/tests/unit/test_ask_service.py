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
        seeded, {"metric": "job_title_stats", "country": "germany", "job_title": "data analysts"}
    )

    assert result.intent == QueryIntent(
        metric="job_title_stats", country="Germany", job_title="Data Analyst"
    )
    assert result.answer == (
        "Data Analyst in Germany: 2 employees, average EUR 70,000 (min EUR 60,000, max EUR 80,000)."
    )


def test_answers_country_question(seeded):
    result = _ask(seeded, {"metric": "country_stats", "country": "India"})
    assert result.answer.startswith("India: 1 employee, average INR 2,000,000")


def test_country_question_without_country_lists_all_countries(seeded):
    result = _ask(seeded, {"metric": "country_stats"})
    assert [row["country"] for row in result.data] == ["Germany", "India"]


def test_answers_org_summary(seeded):
    result = _ask(seeded, {"metric": "org_summary"})
    assert "3 employees across 2 countries" in result.answer


def test_answers_department_question(seeded):
    result = _ask(seeded, {"metric": "department_stats", "department": "finance"})
    assert result.answer.startswith("Finance: 2 employees, average USD 75,600")


def test_unknown_values_fall_back_to_a_helpful_message(seeded):
    result = _ask(
        seeded, {"metric": "job_title_stats", "country": "Germany", "job_title": "Wizard"}
    )
    assert result.intent.metric == "unsupported"
    assert "couldn't" in result.answer.lower()


def test_malformed_llm_output_is_treated_as_unsupported(seeded):
    result = _ask(seeded, {"metric": "drop_tables"})
    assert result.intent.metric == "unsupported"


def test_llm_outage_propagates_as_unavailable(seeded):
    with pytest.raises(LLMUnavailableError):
        _ask(seeded, LLMUnavailableError("down"))
