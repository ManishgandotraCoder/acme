"""The predefined business questions behind the success criterion (docs/REQUIREMENTS.md).

Each names the operation and entities a model should select. The deterministic benchmark
(test_salary_questions.py) feeds that selection in directly and checks the numbers against the
seeded data; the live benchmark (live.py) asks a real model and checks it selects the same.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BenchmarkQuestion:
    category: str
    question: str
    metric: str
    countries: list[str] = field(default_factory=list)
    departments: list[str] = field(default_factory=list)
    job_titles: list[str] = field(default_factory=list)

    @property
    def intent(self) -> dict:
        """What a model that understood the question returns."""
        return {
            "metric": self.metric,
            "countries": self.countries,
            "departments": self.departments,
            "job_titles": self.job_titles,
            "statistic": "median" if "median" in self.question.lower() else "average",
        }


QUESTIONS = [
    BenchmarkQuestion(
        "Salary overview",
        "What are the average and median salaries across the organization?",
        "org_summary",
    ),
    BenchmarkQuestion(
        "Department analysis",
        "What is the average salary in Engineering?",
        "department_stats",
        departments=["Engineering"],
    ),
    BenchmarkQuestion(
        "Department analysis",
        "Which department has the highest median salary?",
        "department_stats",
    ),
    BenchmarkQuestion(
        "Department analysis",
        "Compare Engineering and Sales salaries",
        "department_stats",
        departments=["Engineering", "Sales"],
    ),
    BenchmarkQuestion(
        "Country analysis",
        "How does compensation differ across countries?",
        "country_stats",
    ),
    BenchmarkQuestion(
        "Role analysis",
        "What do data analysts earn in Germany?",
        "job_title_stats",
        countries=["Germany"],
        job_titles=["Data Analyst"],
    ),
    BenchmarkQuestion(
        "Pay equity",
        "What is the salary gap between job levels?",
        "level_stats",
    ),
    BenchmarkQuestion(
        "Outliers",
        "Which employees earn significantly more or less than peers in comparable roles?",
        "outliers",
    ),
    BenchmarkQuestion(
        "Outliers",
        "Show employees earning above their department average",
        "above_department_average",
    ),
    BenchmarkQuestion(
        "Trends",
        "How have salaries changed over the last 12 months?",
        "salary_trends",
    ),
    BenchmarkQuestion(
        "Distribution",
        "How many employees fall into each salary band?",
        "salary_bands",
    ),
]
