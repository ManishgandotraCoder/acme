from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from app.domain.countries import get_country


def _supported_country(value: str) -> str:
    get_country(value)  # raises UnsupportedCountryError (a ValueError) -> 422
    return value


def _not_in_future(value: date) -> date:
    if value > date.today():
        raise ValueError("hire_date cannot be in the future")
    return value


Name = Annotated[str, Field(min_length=1, max_length=120)]
Label = Annotated[str, Field(min_length=1, max_length=80)]
CountryName = Annotated[str, AfterValidator(_supported_country)]
Salary = Annotated[int, Field(gt=0, le=1_000_000_000)]
HireDate = Annotated[date, AfterValidator(_not_in_future)]


class _Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class EmployeeCreate(_Input):
    full_name: Name
    email: EmailStr
    job_title: Label
    department: Label
    country: CountryName
    annual_salary: Salary
    hire_date: HireDate


class EmployeeUpdate(_Input):
    full_name: Name | None = None
    email: EmailStr | None = None
    job_title: Label | None = None
    department: Label | None = None
    country: CountryName | None = None
    annual_salary: Salary | None = None
    hire_date: HireDate | None = None
    salary_change_reason: Annotated[str, Field(max_length=255)] | None = None


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    job_title: str
    department: str
    country: str
    currency: str
    annual_salary: int
    hire_date: date
    created_at: datetime
    updated_at: datetime


class SalaryChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    previous_salary: int
    new_salary: int
    previous_currency: str
    new_currency: str
    reason: str | None
    changed_at: datetime


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


# --- Insights -------------------------------------------------------------------------


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


class CountryOption(BaseModel):
    name: str
    currency: str


class Meta(BaseModel):
    countries: list[CountryOption]
    departments: list[str]
    job_titles: list[str]
