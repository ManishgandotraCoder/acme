from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.orm import Session

from app.modules.employees.models import Employee


class SortField(StrEnum):
    FULL_NAME = "full_name"
    ANNUAL_SALARY = "annual_salary"
    HIRE_DATE = "hire_date"


# Salary sorts use the stored USD value so different currencies compare like with like,
# and so the sort can walk an index instead of sorting every row.
_SORT_COLUMNS = {
    SortField.FULL_NAME: Employee.full_name,
    SortField.ANNUAL_SALARY: Employee.annual_salary_usd,
    SortField.HIRE_DATE: Employee.hire_date,
}


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
        # Emails are stored lower-cased, so plain equality can use the unique index
        # (wrapping the column in lower() would force a full scan).
        stmt = select(Employee).where(Employee.email == email.strip().lower())
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

        sort_column = _SORT_COLUMNS[sort]
        if sort is SortField.ANNUAL_SALARY and filters.country:
            # One country = one currency, so local order equals USD order. Sorting by the
            # local amount is exact (no rounding ties) and walks (country, annual_salary).
            sort_column = Employee.annual_salary
        order = sort_column.desc() if descending else sort_column.asc()
        tie_breaker = Employee.id.desc() if descending else Employee.id.asc()
        stmt = (
            base.order_by(order, tie_breaker)  # id tie-breaker keeps paging stable
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

    def _apply_filters(self, stmt: Select, f: EmployeeFilter) -> Select:
        if f.search and f.search.strip():
            stmt = stmt.where(self._search_condition(f.search.strip()))
        if f.country:
            stmt = stmt.where(Employee.country == f.country)
        if f.department:
            stmt = stmt.where(Employee.department == f.department)
        if f.job_title:
            stmt = stmt.where(Employee.job_title == f.job_title)
        return stmt

    @staticmethod
    def _search_condition(term: str) -> ColumnElement[bool]:
        # Case-insensitive substring match, served by the trigram GIN indexes (terms of 3+
        # characters). autoescape: '%' and '_' typed by the user are matched literally.
        return or_(
            Employee.full_name.icontains(term, autoescape=True),
            Employee.email.icontains(term, autoescape=True),
        )
