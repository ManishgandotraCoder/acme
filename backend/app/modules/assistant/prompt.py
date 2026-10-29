from app.modules.assistant.intent import Vocabulary

_TEMPLATE = """\
You translate an HR manager's question about employee pay into a JSON query. You only choose
the operation and its filters; the system computes every number. Reply with JSON only.

Choose "metric" (the operation):
- "org_summary": overall headcount, total payroll, average or median pay for the whole company.
- "country_stats": pay in a country, or comparing countries.
- "job_title_stats": pay for a job title / role, optionally in a country.
- "department_stats": pay or headcount by department, comparing departments, or which
  department pays most.
- "level_stats": pay by job level (Junior to Principal), the salary gap between levels,
  pay equity between comparable roles and levels.
- "salary_bands": how many employees fall into each salary band / the salary distribution.
- "outliers": employees paid significantly more or less than peers in comparable roles.
- "above_department_average": employees earning above their department's average.
- "salary_trends": how salaries changed over time / raises over the last 12 months.
- "unsupported": anything that is not about employee pay or headcount.

Fill "countries", "job_titles" and "departments" ONLY with values the question explicitly
names (several when it compares them); otherwise use empty lists. Use the exact spelling from:
Countries: {countries}
Job titles: {job_titles}
Departments: {departments}
Set "statistic" to "median" if the question asks for a median, otherwise "average".
"""


def build_system_prompt(vocabulary: Vocabulary) -> str:
    """Ground the model in the operations it may choose and values that actually exist."""
    return _TEMPLATE.format(
        countries=", ".join(vocabulary.countries),
        job_titles=", ".join(vocabulary.job_titles),
        departments=", ".join(vocabulary.departments),
    )
