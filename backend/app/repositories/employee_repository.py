from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.orm import Session

from app.domain.countries import SUPPORTED_COUNTRIES
from app.models import Employee


class SortField(StrEnum):
    FULL_NAME = "full_name"
    ANNUAL_SALARY = "annual_salary"
    HIRE_DATE = "hire_date"


@dataclass(frozen=True, slots=True)
class EmployeeFilter:
    search: str | None = None
    country: str | None = None
    department: str | None = None
    job_title: str | None = None


class EmployeeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, employee: Employee) -> Employee:
        self._session.add(employee)
        self._session.flush()
        return employee

    def get(self, employee_id: int) -> Employee | None:
        return self._session.get(Employee, employee_id)

    def get_by_email(self, email: str) -> Employee | None:
        stmt = select(Employee).where(func.lower(Employee.email) == email.lower())
        return self._session.scalars(stmt).first()

    def delete(self, employee: Employee) -> None:
        self._session.delete(employee)
        self._session.flush()

    def search(
        self,
        filters: EmployeeFilter,
        *,
        page: int = 1,
        page_size: int = 25,
        sort: SortField = SortField.FULL_NAME,
        descending: bool = False,
    ) -> tuple[list[Employee], int]:
        base = self._apply_filters(select(Employee), filters)
        total = self._session.scalar(select(func.count()).select_from(base.subquery())) or 0

        sort_column = (
            _salary_in_usd() if sort is SortField.ANNUAL_SALARY else getattr(Employee, sort.value)
        )
        order = sort_column.desc() if descending else sort_column.asc()
        stmt = (
            base.order_by(order, Employee.id)  # id tie-breaker keeps paging stable
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self._session.scalars(stmt)), total

    def distinct_departments(self) -> list[str]:
        return self._distinct(Employee.department)

    def distinct_job_titles(self) -> list[str]:
        return self._distinct(Employee.job_title)

    def _distinct(self, column) -> list[str]:
        return list(self._session.scalars(select(column).distinct().order_by(column)))

    @staticmethod
    def _apply_filters(stmt: Select, f: EmployeeFilter) -> Select:
        if f.search:
            pattern = f"%{f.search.strip()}%"
            stmt = stmt.where(or_(Employee.full_name.ilike(pattern), Employee.email.ilike(pattern)))
        if f.country:
            stmt = stmt.where(Employee.country == f.country)
        if f.department:
            stmt = stmt.where(Employee.department == f.department)
        if f.job_title:
            stmt = stmt.where(Employee.job_title == f.job_title)
        return stmt


def _salary_in_usd():
    """Salaries are in local currency; ranking them must compare like with like."""
    rates = {c.name: c.usd_rate for c in SUPPORTED_COUNTRIES}
    return Employee.annual_salary * case(rates, value=Employee.country, else_=1.0)
