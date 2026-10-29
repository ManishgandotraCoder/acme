from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.employees.errors import (
    CurrencyChangeRequiresSalaryError,
    DuplicateEmailError,
    EmployeeNotFoundError,
)
from app.modules.employees.models import Employee, SalaryChange
from app.modules.employees.repository import EmployeeFilter, EmployeeRepository, SortField
from app.modules.employees.schemas import EmployeeCreate, EmployeeUpdate
from app.shared.countries import currency_for


class EmployeeService:
    """Use-cases for managing employees. Owns the transaction boundary."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = EmployeeRepository(session)

    def create(self, data: EmployeeCreate) -> Employee:
        email = data.email.lower()
        self._ensure_email_free(email)
        employee = self._repo.add(
            Employee(
                **data.model_dump(exclude={"email"}),
                email=email,
                currency=currency_for(data.country),
            )
        )
        self._session.commit()
        return employee

    def get(self, employee_id: int) -> Employee:
        employee = self._repo.get(employee_id)
        if employee is None:
            raise EmployeeNotFoundError(employee_id)
        return employee

    def search(
        self,
        filters: EmployeeFilter,
        *,
        page: int,
        page_size: int,
        sort: SortField,
        descending: bool,
    ) -> tuple[list[Employee], int]:
        return self._repo.search(
            filters, page=page, page_size=page_size, sort=sort, descending=descending
        )

    def update(self, employee_id: int, data: EmployeeUpdate) -> Employee:
        employee = self.get(employee_id)
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        reason = changes.pop("salary_change_reason", None)

        if "email" in changes:
            changes["email"] = changes["email"].lower()
            if changes["email"] != employee.email:
                self._ensure_email_free(changes["email"])

        previous_salary, previous_currency = employee.annual_salary, employee.currency
        new_currency = currency_for(changes.get("country", employee.country))
        if new_currency != previous_currency and "annual_salary" not in changes:
            raise CurrencyChangeRequiresSalaryError(previous_currency, new_currency)

        for field, value in changes.items():
            setattr(employee, field, value)
        employee.currency = new_currency

        if (employee.annual_salary, new_currency) != (previous_salary, previous_currency):
            self._session.add(
                SalaryChange(
                    employee=employee,
                    previous_salary=previous_salary,
                    new_salary=employee.annual_salary,
                    previous_currency=previous_currency,
                    new_currency=new_currency,
                    reason=reason,
                )
            )

        self._session.commit()
        return employee

    def delete(self, employee_id: int) -> None:
        self._repo.delete(self.get(employee_id))
        self._session.commit()

    def salary_history(self, employee_id: int) -> list[SalaryChange]:
        self.get(employee_id)
        stmt = (
            select(SalaryChange)
            .where(SalaryChange.employee_id == employee_id)
            .order_by(SalaryChange.changed_at.desc(), SalaryChange.id.desc())
        )
        return list(self._session.scalars(stmt))

    def _ensure_email_free(self, email: str) -> None:
        if self._repo.get_by_email(email) is not None:
            raise DuplicateEmailError(email)
