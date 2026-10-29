from pydantic import BaseModel


class OrgSummary(BaseModel):
    headcount: int
    country_count: int
    total_payroll_usd: int
    average_salary_usd: int
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
