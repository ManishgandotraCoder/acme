"""Deterministic generation of realistic employee rows for seeding.

Salary bands are expressed in USD for a US-based role, scaled by a country pay level and
converted to local currency, then rounded to a "human" number (as HR would record it).
Within a band, the job level sets the position: higher levels sit higher in the band.
"""

import random
from datetime import date, timedelta
from pathlib import Path

from app.shared.countries import get_country, to_usd
from app.shared.levels import JOB_LEVELS, level_rank

DATA_DIR = Path(__file__).parent / "data"

# country -> (share of workforce, pay level relative to the US in USD terms)
COUNTRY_PROFILE: dict[str, tuple[float, float]] = {
    "United States": (0.30, 1.00),
    "India": (0.20, 0.30),
    "United Kingdom": (0.10, 0.75),
    "Germany": (0.08, 0.80),
    "Canada": (0.07, 0.80),
    "France": (0.05, 0.70),
    "Brazil": (0.05, 0.35),
    "Australia": (0.05, 0.80),
    "Singapore": (0.05, 0.75),
    "Japan": (0.05, 0.60),
}

# department -> {job_title: (min USD, max USD) for a US-based employee}
ROLES: dict[str, dict[str, tuple[int, int]]] = {
    "Engineering": {
        "Software Engineer": (100_000, 160_000),
        "Senior Software Engineer": (140_000, 210_000),
        "Engineering Manager": (170_000, 250_000),
        "QA Engineer": (80_000, 120_000),
    },
    "Data": {
        "Data Analyst": (70_000, 110_000),
        "Data Scientist": (110_000, 170_000),
    },
    "Product": {
        "Product Manager": (120_000, 190_000),
        "Product Designer": (95_000, 150_000),
    },
    "Sales": {
        "Account Executive": (70_000, 140_000),
        "Sales Manager": (110_000, 180_000),
    },
    "Marketing": {
        "Marketing Specialist": (60_000, 95_000),
        "Marketing Manager": (100_000, 160_000),
    },
    "Finance": {
        "Accountant": (60_000, 95_000),
        "Financial Analyst": (70_000, 115_000),
    },
    "People": {
        "HR Generalist": (55_000, 85_000),
        "Recruiter": (60_000, 95_000),
    },
    "Operations": {
        "Operations Coordinator": (45_000, 70_000),
        "Customer Support Specialist": (40_000, 60_000),
    },
}
# Headcount weight per department (engineering-heavy org).
DEPARTMENT_WEIGHTS = {
    "Engineering": 0.35,
    "Data": 0.08,
    "Product": 0.08,
    "Sales": 0.15,
    "Marketing": 0.07,
    "Finance": 0.06,
    "People": 0.05,
    "Operations": 0.16,
}

# Share of the workforce at each level (a pyramid), in JOB_LEVELS order.
LEVEL_WEIGHTS = (0.20, 0.35, 0.25, 0.15, 0.05)

HIRE_DATE_START = date(2010, 1, 1)
HIRE_DATE_END = date(2026, 9, 30)  # fixed so output is reproducible

# Two years of salary history, so "last 12 months" trends have data. Fixed dates keep the seed
# reproducible; trend questions take an explicit "as of" date in tests.
HISTORY_START = date(2024, 10, 1)
HISTORY_END = HIRE_DATE_END
HISTORY_AUTHOR = "HRIS import"
# reason -> (probability per review cycle, raise range)
_REVIEW = ("Annual review", (0.02, 0.06))
_PROMOTION = ("Promotion", (0.08, 0.15))
_PROMOTION_RATE = 0.12


def load_names() -> tuple[list[str], list[str]]:
    def read(name: str) -> list[str]:
        return [line.strip() for line in (DATA_DIR / name).read_text().splitlines() if line.strip()]

    return read("first_names.txt"), read("last_names.txt")


def generate_employees(
    count: int, rng: random.Random, first_names: list[str], last_names: list[str]
) -> list[dict]:
    countries = list(COUNTRY_PROFILE)
    country_weights = [COUNTRY_PROFILE[c][0] for c in countries]
    departments = list(DEPARTMENT_WEIGHTS)
    department_weights = list(DEPARTMENT_WEIGHTS.values())
    hire_span_days = (HIRE_DATE_END - HIRE_DATE_START).days

    rows = []
    for i in range(count):
        first, last = rng.choice(first_names), rng.choice(last_names)
        country = rng.choices(countries, country_weights)[0]
        department = rng.choices(departments, department_weights)[0]
        job_title, (low, high) = rng.choice(list(ROLES[department].items()))
        level = rng.choices(JOB_LEVELS, LEVEL_WEIGHTS)[0]

        salary = _local_salary(_band_position(low, high, level, rng), country)
        rows.append(
            {
                "full_name": f"{first} {last}",
                # Index suffix guarantees uniqueness across 10k rows with repeated names.
                "email": f"{first}.{last}.{i + 1}@acme.com".lower(),
                "job_title": job_title,
                "job_level": level,
                "department": department,
                "country": country,
                "currency": get_country(country).currency,
                "annual_salary": salary,
                # Bulk Core inserts bypass ORM events, so the derived value is set here.
                "annual_salary_usd": to_usd(salary, country),
                "hire_date": HIRE_DATE_START + timedelta(days=rng.randrange(hire_span_days)),
            }
        )
    return rows


def _band_position(low: int, high: int, level: str, rng: random.Random) -> float:
    """Each level owns an overlapping slice of the band; Principal sits at the top."""
    slice_start = level_rank(level) / len(JOB_LEVELS)
    position = slice_start + rng.uniform(0, 1.6 / len(JOB_LEVELS))
    return low + (high - low) * min(position, 1.0)


def _local_salary(us_usd: float, country: str) -> int:
    info = get_country(country)
    local = us_usd * COUNTRY_PROFILE[country][1] / info.usd_rate
    step = 10_000 if local >= 1_000_000 else 500  # INR/JPY salaries round to bigger steps
    return max(step, round(local / step) * step)


def generate_salary_history(employees: list[dict], rng: random.Random) -> list[dict]:
    """Past salary changes for generated employees, ending at each one's current salary.

    Each employee has up to one review per year in the window (after their hire date), some of
    them promotions. Amounts are derived backwards from the current salary, so the newest change
    always lands on ``annual_salary``. Rows carry ``employee_index`` (position in
    ``employees``); the caller maps it to a database id.
    """
    history = []
    for index, employee in enumerate(employees):
        dates = _review_dates(employee["hire_date"], rng)
        salary = employee["annual_salary"]
        for effective in reversed(dates):  # newest first, walking back in time
            reason, (low, high) = _PROMOTION if rng.random() < _PROMOTION_RATE else _REVIEW
            previous = round(salary / (1 + rng.uniform(low, high)))
            history.append(
                {
                    "employee_index": index,
                    "previous_salary": previous,
                    "new_salary": salary,
                    "previous_currency": employee["currency"],
                    "new_currency": employee["currency"],
                    "reason": reason,
                    "effective_date": effective,
                    "changed_by": HISTORY_AUTHOR,
                }
            )
            salary = previous
    return history


def _review_dates(hired: date, rng: random.Random) -> list[date]:
    """One review date per year of the history window that the employee was present for."""
    dates = []
    year_start = HISTORY_START
    while year_start <= HISTORY_END:
        offset = rng.randrange(365)
        effective = min(year_start + timedelta(days=offset), HISTORY_END)
        if effective >= hired and rng.random() < 0.85:  # some reviews bring no raise
            dates.append(effective)
        year_start = year_start.replace(year=year_start.year + 1)
    return dates
