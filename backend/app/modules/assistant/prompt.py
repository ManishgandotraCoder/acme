from app.modules.assistant.intent import Vocabulary

_TEMPLATE = """\
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


def build_system_prompt(vocabulary: Vocabulary) -> str:
    """Ground the model in values that actually exist in the data."""
    return _TEMPLATE.format(
        countries=", ".join(vocabulary.countries),
        job_titles=", ".join(vocabulary.job_titles),
        departments=", ".join(vocabulary.departments),
    )
