from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from app.shared.countries import get_country
from app.shared.levels import JOB_LEVELS


def _supported_country(value: str) -> str:
    get_country(value)  # raises UnsupportedCountryError (a ValueError) -> 422
    return value


def _not_in_future(value: date) -> date:
    if value > date.today():
        raise ValueError("date cannot be in the future")
    return value


def _known_level(value: str) -> str:
    if value not in JOB_LEVELS:
        raise ValueError(f"job_level must be one of {', '.join(JOB_LEVELS)}")
    return value


Name = Annotated[str, Field(min_length=1, max_length=120)]
Label = Annotated[str, Field(min_length=1, max_length=80)]
CountryName = Annotated[str, AfterValidator(_supported_country)]
Salary = Annotated[int, Field(gt=0, le=1_000_000_000)]
PastDate = Annotated[date, AfterValidator(_not_in_future)]
JobLevel = Annotated[str, AfterValidator(_known_level)]


class _Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class EmployeeCreate(_Input):
    full_name: Name
    email: EmailStr
    job_title: Label
    job_level: JobLevel
    department: Label
    country: CountryName
    annual_salary: Salary
    hire_date: PastDate


class EmployeeUpdate(_Input):
    full_name: Name | None = None
    email: EmailStr | None = None
    job_title: Label | None = None
    job_level: JobLevel | None = None
    department: Label | None = None
    country: CountryName | None = None
    annual_salary: Salary | None = None
    hire_date: PastDate | None = None
    salary_change_reason: Annotated[str, Field(max_length=255)] | None = None
    # Defaults to today. Only used when the salary or currency changes.
    salary_effective_date: PastDate | None = None


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    job_title: str
    job_level: str
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
    effective_date: date
    changed_by: str
    changed_at: datetime


class CountryOption(BaseModel):
    name: str
    currency: str


class Meta(BaseModel):
    countries: list[CountryOption]
    job_levels: list[str]
    departments: list[str]
    job_titles: list[str]
