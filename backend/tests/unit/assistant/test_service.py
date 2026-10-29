from datetime import date

import pytest

from app.core.actor import VIEW_INDIVIDUAL_PAY, Actor
from app.modules.assistant.llm import LLMUnavailableError
from app.modules.assistant.service import AskService
from app.modules.employees.models import SalaryChange
from tests.conftest import build_employee

HR_MANAGER = Actor(name="HR Manager", permissions=frozenset({VIEW_INDIVIDUAL_PAY}))
TEAM_LEAD = Actor(name="Team lead", permissions=frozenset())
TODAY = date(2026, 9, 30)


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


def _ask(session, llm_response, question="q", actor=HR_MANAGER):
    service = AskService(session, FakeLLM(llm_response), actor=actor, today=lambda: TODAY)
    return service.ask(question)


def test_prompt_grounds_the_model_in_real_values_and_operations(seeded):
    llm = FakeLLM({"metric": "org_summary"})
    AskService(seeded, llm, actor=HR_MANAGER).ask("How much do we pay overall?")

    system, user = llm.calls[0]
    assert "Germany" in system and "Data Analyst" in system and "Finance" in system
    assert "salary_trends" in system and "outliers" in system
    assert user == "How much do we pay overall?"


# --- Answers come from the database, with a table, a chart and the data scope -----------------


def test_answers_job_title_question_with_numbers_from_the_database(seeded):
    result = _ask(
        seeded,
        {"metric": "job_title_stats", "countries": ["germany"], "job_titles": ["data analysts"]},
        question="What do data analysts earn in Germany?",
    )

    assert (result.intent.countries, result.intent.job_titles) == (["Germany"], ["Data Analyst"])
    assert result.kind == "answer"
    assert result.answer == (
        "Data Analyst in Germany: 2 employees, average EUR 70,000 (min EUR 60,000, max EUR 80,000)."
    )
    assert result.table.rows[0]["average_salary"] == 70_000
    assert "Germany" in result.scope


def test_answers_a_single_country(seeded):
    result = _ask(seeded, {"metric": "country_stats"}, "Pay in India?")
    assert result.answer.startswith("India: 1 employee, average INR 2,000,000")


def test_compares_all_countries_in_usd_with_a_chart(seeded):
    result = _ask(seeded, {"metric": "country_stats"}, "Compare average salaries across countries")

    assert [row["country"] for row in result.table.rows] == ["Germany", "India"]
    assert result.chart.x == "country" and result.chart.y == "average_salary_usd"
    assert "USD" in result.scope and "FX" in result.scope


def test_answers_org_summary_with_average_and_median(seeded):
    result = _ask(seeded, {"metric": "org_summary"})
    assert "3 employees across 2 countries" in result.answer
    assert "median USD 64,800" in result.answer


def test_answers_department_question(seeded):
    result = _ask(seeded, {"metric": "department_stats"}, "Finance pay?")
    assert result.answer.startswith("Finance: 2 employees, average USD 75,600")


def test_compares_named_departments_only(seeded):
    result = _ask(
        seeded, {"metric": "department_stats"}, "Compare Engineering and Finance salaries"
    )
    assert [row["department"] for row in result.table.rows] == ["Finance", "Engineering"]


def test_highest_median_department_leads_the_answer(seeded):
    result = _ask(
        seeded, {"metric": "department_stats"}, "Which department has the highest median salary?"
    )
    assert result.answer.startswith("Finance has the highest median salary (USD 75,600).")
    assert result.chart.y == "median_salary_usd"


def test_answers_salary_gap_between_levels(session):
    session.add_all(
        [
            build_employee(email="j@example.com", job_level="Junior", annual_salary=50_000),
            build_employee(email="s@example.com", job_level="Senior", annual_salary=60_000),
        ]
    )
    session.commit()

    result = _ask(session, {"metric": "level_stats"}, "What is the salary gap between job levels?")

    assert [row["job_level"] for row in result.table.rows] == ["Junior", "Senior"]
    assert "Senior USD 76,200" in result.answer
    assert "same job title and country" in result.scope


def test_answers_salary_band_distribution(seeded):
    result = _ask(seeded, {"metric": "salary_bands"}, "How many employees fall in each band?")
    assert result.answer.startswith("Employees by annual salary (USD): Under USD 50k: 1;")
    assert result.chart.x == "label"


def test_answers_salary_trends_for_the_last_12_months(seeded):
    ada = build_employee(email="ada@example.com")
    seeded.add(
        SalaryChange(
            employee=ada,
            previous_salary=100_000,
            new_salary=105_000,
            previous_currency="GBP",
            new_currency="GBP",
            effective_date=date(2026, 3, 1),
            changed_by="HR",
        )
    )
    seeded.commit()

    result = _ask(seeded, {"metric": "salary_trends"}, "How have salaries changed this year?")

    assert result.answer.startswith(
        "Over the last 12 months (Oct 2025 – Sep 2026): 1 salary change for 1 employee, "
        "average raise 5.0%."
    )
    assert len(result.table.rows) == 12


# --- Individual-level results respect permissions ------------------------------------------


@pytest.fixture
def peers(session):
    session.add_all(
        build_employee(email=f"p{i}@example.com", full_name=f"Peer {i}", annual_salary=100_000)
        for i in range(5)
    )
    session.add(
        build_employee(email="o@example.com", full_name="Olive Outlier", annual_salary=200_000)
    )
    session.commit()
    return session


def test_outliers_name_people_for_someone_allowed_to_see_individual_pay(peers):
    result = _ask(peers, {"metric": "outliers"}, "Who is paid far more than peers?")
    assert result.kind == "answer"
    assert result.table.rows[0]["full_name"] == "Olive Outlier"
    assert "+100.0%" in result.answer


@pytest.mark.parametrize("metric", ["outliers", "above_department_average"])
def test_individual_results_are_refused_without_permission(peers, metric):
    result = _ask(peers, {"metric": metric}, "Who earns most?", actor=TEAM_LEAD)

    assert result.kind == "forbidden"
    assert result.table is None
    assert "Olive" not in result.answer
    assert result.suggestions  # points to aggregate questions instead


def test_small_groups_are_hidden_from_someone_without_individual_access(seeded):
    result = _ask(seeded, {"metric": "country_stats"}, "Pay in India?", actor=TEAM_LEAD)

    assert "2,000,000" not in result.answer  # India has one employee
    assert "fewer than 3" in result.answer
    assert result.table.rows[0]["average_salary"] is None


def test_answers_above_department_average(peers):
    result = _ask(peers, {"metric": "above_department_average"}, "Who earns above average?")
    assert result.answer.startswith("1 of 6 employees earn above their department's average")


# --- Ambiguity and unsupported questions ---------------------------------------------------


def test_ambiguous_role_asks_which_one_is_meant(session):
    session.add_all(
        [
            build_employee(email="a@example.com", job_title="Software Engineer"),
            build_employee(email="b@example.com", job_title="QA Engineer"),
        ]
    )
    session.commit()

    result = _ask(session, {"metric": "job_title_stats"}, "How much do engineers make?")

    assert result.kind == "clarification"
    assert "QA Engineer" in result.answer and "Software Engineer" in result.answer
    assert "What do QA Engineers earn?" in result.suggestions


def test_role_question_without_role_or_country_asks_for_one(seeded):
    result = _ask(seeded, {"metric": "job_title_stats"}, "What do people earn by role?")
    assert result.kind == "clarification"


def test_model_can_decline_off_topic_questions(seeded):
    result = _ask(seeded, {"metric": "unsupported"}, "What's the weather tomorrow?")
    assert result.kind == "unsupported"
    assert "couldn't" in result.answer.lower()
    assert result.suggestions


# --- Regression tests from running against the real llama3.2 model -------------------


def test_entities_omitted_by_the_model_are_recovered_from_the_question(seeded):
    result = _ask(
        seeded,
        {"metric": "job_title_stats", "job_titles": ["Data Analyst"]},
        question="What is the average salary of data analysts in Germany?",
    )
    assert (result.intent.countries, result.intent.job_titles) == (["Germany"], ["Data Analyst"])


def test_filters_invented_by_the_model_are_ignored(seeded):
    result = _ask(
        seeded,
        {"metric": "department_stats", "departments": ["Finance"]},
        question="Which department has the highest average pay?",
    )
    assert result.intent.departments == []
    assert result.answer.startswith("Finance has the highest average salary")
    assert len(result.table.rows) == 2


def test_unknown_values_invented_by_the_model_do_not_block_the_answer(seeded):
    result = _ask(
        seeded,
        {
            "metric": "job_title_stats",
            "job_titles": ["Software Engineer"],
            "departments": ["IT/Software Development"],
        },
        question="How much do we pay software engineers in India?",
    )
    assert result.intent.departments == []
    assert (result.intent.countries, result.intent.job_titles) == (["India"], ["Software Engineer"])


def test_unknown_job_title_is_dropped_and_answer_states_its_real_scope(seeded):
    result = _ask(
        seeded,
        {"metric": "job_title_stats", "countries": ["Germany"], "job_titles": ["Wizard"]},
        question="What do wizards earn in Germany?",
    )
    assert result.intent.job_titles == []
    assert result.answer.startswith("Average salary by job title in Germany")


def test_longest_job_title_mention_wins(session):
    session.add_all(
        [
            build_employee(email="a@example.com", job_title="Software Engineer"),
            build_employee(email="b@example.com", job_title="Senior Software Engineer"),
        ]
    )
    session.commit()
    result = _ask(session, {"metric": "job_title_stats"}, "Senior software engineer pay in the UK")
    assert result.intent.job_titles == ["Senior Software Engineer"]


def test_malformed_llm_output_is_treated_as_unsupported(seeded):
    result = _ask(seeded, {"metric": "drop_tables"})
    assert result.intent.metric == "unsupported"


def test_llm_outage_propagates_as_unavailable(seeded):
    with pytest.raises(LLMUnavailableError):
        _ask(seeded, LLMUnavailableError("down"))


# --- Regression tests from running the salary-intelligence questions on llama3.2 ------------


def test_a_department_question_is_not_answered_with_a_similarly_named_role(seeded):
    result = _ask(
        seeded,
        {
            "metric": "job_title_stats",
            "job_titles": ["Engineering Manager"],
            "departments": ["Engineering"],
        },
        question="What is the average salary in Engineering?",
    )
    assert result.intent.metric == "department_stats"
    assert (result.intent.departments, result.intent.job_titles) == (["Engineering"], [])
    assert result.answer.startswith("Engineering: 1 employee")


def test_comparing_departments_classified_as_a_role_question_still_compares_them(seeded):
    result = _ask(
        seeded,
        {"metric": "job_title_stats", "departments": ["Engineering", "Finance"]},
        question="Compare Engineering and Finance salaries",
    )
    assert result.kind == "answer"
    assert [row["department"] for row in result.table.rows] == ["Finance", "Engineering"]


def test_roles_guessed_by_the_model_for_a_vague_word_still_get_a_clarifying_question(session):
    session.add_all(
        build_employee(email=f"{i}@example.com", job_title=title)
        for i, title in enumerate(["Software Engineer", "Senior Software Engineer", "QA Engineer"])
    )
    session.commit()

    result = _ask(
        session,
        {
            "metric": "job_title_stats",
            "job_titles": ["Senior Software Engineer", "Software Engineer"],
        },
        question="How much do engineers make?",
    )

    assert result.kind == "clarification"
    assert "QA Engineer" in result.answer


def test_level_answer_separates_like_for_like_gaps_from_org_wide_medians(session):
    session.add_all(
        [
            build_employee(email="j@example.com", job_level="Junior", annual_salary=50_000),
            build_employee(email="s@example.com", job_level="Senior", annual_salary=60_000),
        ]
    )
    session.commit()

    result = _ask(session, {"metric": "level_stats"}, "What is the salary gap between job levels?")

    assert result.answer.startswith(
        "Like for like (same job title and country), Senior is paid +20.0% vs Junior."
    )
    assert (
        "Org-wide median pay, which also reflects where each level's people work" in result.answer
    )
