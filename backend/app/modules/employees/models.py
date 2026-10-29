from datetime import UTC, date, datetime

from sqlalchemy import DDL, Date, DateTime, ForeignKey, Index, Integer, String, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.employees import search_index
from app.shared.countries import to_usd


def utcnow() -> datetime:
    return datetime.now(UTC)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)  # stored lower-case
    job_title: Mapped[str] = mapped_column(String(80))
    department: Mapped[str] = mapped_column(String(80))
    country: Mapped[str] = mapped_column(String(60))
    currency: Mapped[str] = mapped_column(String(3))
    # Whole units of local currency. Annual salaries are never fractional in practice,
    # and integers avoid float rounding in aggregates.
    annual_salary: Mapped[int] = mapped_column(Integer)
    # Derived from annual_salary + country (kept in sync below); stored so "highest paid"
    # sorting across currencies can use an index instead of sorting every row.
    annual_salary_usd: Mapped[int] = mapped_column(Integer, index=True)
    hire_date: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    salary_changes: Mapped[list["SalaryChange"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="desc(SalaryChange.changed_at)",
    )

    # Each index serves a measured read path (docs/adr/0006-indexing.md;
    # enforced by tests/unit/test_query_plans.py). Composite indexes end in the sort/aggregate
    # column so filtered lists need no in-memory sort and insights read only the index.
    __table_args__ = (
        # Directory filtered by one column, sorted by name.
        Index("ix_employees_country_full_name", "country", "full_name"),
        Index("ix_employees_department_full_name", "department", "full_name"),
        Index("ix_employees_job_title_full_name", "job_title", "full_name"),
        # Insights: covering indexes for GROUP BY + aggregates + median.
        Index("ix_employees_country_salary", "country", "annual_salary"),
        Index("ix_employees_country_job_title_salary", "country", "job_title", "annual_salary"),
        Index("ix_employees_department_country_salary", "department", "country", "annual_salary"),
        Index("ix_employees_country_department_salary", "country", "department", "annual_salary"),
    )


@event.listens_for(Employee, "before_insert")
@event.listens_for(Employee, "before_update")
def _sync_salary_usd(_mapper, _connection, employee: Employee) -> None:
    employee.annual_salary_usd = to_usd(employee.annual_salary, employee.country)


for _statement in search_index.CREATE_STATEMENTS:
    event.listen(Employee.__table__, "after_create", DDL(_statement).execute_if(dialect="sqlite"))
for _statement in search_index.DROP_STATEMENTS:
    event.listen(Employee.__table__, "before_drop", DDL(_statement).execute_if(dialect="sqlite"))


class SalaryChange(Base):
    __tablename__ = "salary_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    previous_salary: Mapped[int] = mapped_column(Integer)
    new_salary: Mapped[int] = mapped_column(Integer)
    previous_currency: Mapped[str] = mapped_column(String(3))
    new_currency: Mapped[str] = mapped_column(String(3))
    reason: Mapped[str | None] = mapped_column(String(255))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    employee: Mapped[Employee] = relationship(back_populates="salary_changes")

    # History is read newest-first per employee.
    __table_args__ = (
        Index("ix_salary_changes_employee_changed_at", "employee_id", "changed_at", "id"),
    )
