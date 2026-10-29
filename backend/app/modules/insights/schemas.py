from pydantic import BaseModel


class OrgSummary(BaseModel):
    headcount: int
    country_count: int
    total_payroll_usd: int
    average_salary_usd: int
    median_salary_usd: int
    fx_rates_as_of: str


class CountryStats(BaseModel):
    country: str
    currency: str
    headcount: int
    min_salary: int
    max_salary: int
    average_salary: int
    median_salary: int
    average_salary_usd: int
    median_salary_usd: int


class JobTitleStats(BaseModel):
    job_title: str
    currency: str
    headcount: int
    min_salary: int
    max_salary: int
    average_salary: int


class DepartmentStats(BaseModel):
    department: str
    headcount: int
    total_payroll_usd: int
    average_salary_usd: int
    median_salary_usd: int


class LevelStats(BaseModel):
    job_level: str
    headcount: int
    average_salary_usd: int
    median_salary_usd: int
    # Median pay vs the level below for the same job title in the same country, in percent
    # (weighted over such groups); None for the first level or when no group has both levels.
    gap_to_previous_pct: float | None


class SalaryBand(BaseModel):
    label: str
    min_usd: int
    max_usd: int | None  # exclusive; None = open-ended
    headcount: int


class PayOutlier(BaseModel):
    """An employee paid far from peers with the same job title, level and country."""

    employee_id: int
    full_name: str
    job_title: str
    job_level: str
    department: str
    country: str
    currency: str
    annual_salary: int
    peer_median_salary: int
    peer_count: int
    deviation_pct: float


class DepartmentAboveAverage(BaseModel):
    department: str
    headcount: int
    above: int
    average_salary_usd: int


class EmployeeAboveAverage(BaseModel):
    employee_id: int
    full_name: str
    job_title: str
    department: str
    country: str
    annual_salary_usd: int
    department_average_usd: int
    above_by_usd: int


class AboveAverageReport(BaseModel):
    headcount: int
    employees_above: int
    departments: list[DepartmentAboveAverage]
    top: list[EmployeeAboveAverage]


class MonthlyTrend(BaseModel):
    month: str  # YYYY-MM
    changes: int
    # Mean raise in percent, over changes that kept the currency (a currency move isn't a raise).
    average_raise_pct: float | None


class SalaryTrend(BaseModel):
    start: str
    end: str
    changes: int
    employees: int
    average_raise_pct: float | None
    months: list[MonthlyTrend]
