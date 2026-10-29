from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.countries import to_usd


def utcnow() -> datetime:
    return datetime.now(UTC)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)  # stored lower-case
    job_title: Mapped[str] = mapped_column(String(80))
    job_level: Mapped[str] = mapped_column(String(20))  # one of app.shared.levels.JOB_LEVELS
    department: Mapped[str] = mapped_column(String(80))
    country: Mapped[str] = mapped_column(String(60))
    currency: Mapped[str] = mapped_column(String(3))
    # Whole units of local currency. Annual salaries are never fractional in practice,
    # and integers avoid float rounding in aggregates.
    annual_salary: Mapped[int] = mapped_column(Integer)
    # Derived from annual_salary + country (kept in sync below); stored so "highest paid"
    # sorting across currencies can use an index instead of sorting every row.
    annual_salary_usd: Mapped[int] = mapped_column(Integer)
    hire_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    salary_changes: Mapped[list["SalaryChange"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="desc(SalaryChange.effective_date)",
    )

    # Each index serves a measured read path (docs/adr/0006-indexing.md;
    # enforced by tests/unit/test_query_plans.py). List indexes end in (sort column, id): the
    # repository always breaks ties by id, and Postgres (unlike SQLite) does not append it to
    # indexes implicitly, so without it every page would need an extra sort.
    __table_args__ = (
        # Directory sorts.
        Index("ix_employees_full_name_id", "full_name", "id"),
        Index("ix_employees_annual_salary_usd_id", "annual_salary_usd", "id"),
        Index("ix_employees_hire_date_id", "hire_date", "id"),
        # Directory filtered by one column, sorted by name.
        Index("ix_employees_country_full_name_id", "country", "full_name", "id"),
        Index("ix_employees_department_full_name_id", "department", "full_name", "id"),
        Index("ix_employees_job_title_full_name_id", "job_title", "full_name", "id"),
        Index("ix_employees_job_level_full_name_id", "job_level", "full_name", "id"),
        Index("ix_employees_currency_full_name_id", "currency", "full_name", "id"),
        # Insights: covering indexes for GROUP BY + aggregates + median. (country, salary, id)
        # also serves the directory's country filter + salary sort.
        Index("ix_employees_country_salary_id", "country", "annual_salary", "id"),
        Index("ix_employees_country_job_title_salary", "country", "job_title", "annual_salary"),
        Index("ix_employees_department_country_salary", "department", "country", "annual_salary"),
        Index("ix_employees_country_department_salary", "country", "department", "annual_salary"),
        # Peer groups (same title, country, level): like-for-like level gaps and outliers.
        Index(
            "ix_employees_title_country_level_salary",
            "job_title",
            "country",
            "job_level",
            "annual_salary",
        ),
        # Search: trigram GIN indexes let ILIKE '%term%' use an index (pg_trgm).
        Index(
            "ix_employees_full_name_trgm",
            "full_name",
            postgresql_using="gin",
            postgresql_ops={"full_name": "gin_trgm_ops"},
        ),
        Index(
            "ix_employees_email_trgm",
            "email",
            postgresql_using="gin",
            postgresql_ops={"email": "gin_trgm_ops"},
        ),
    )


@event.listens_for(Employee, "before_insert")
@event.listens_for(Employee, "before_update")
def _sync_salary_usd(_mapper, _connection, employee: Employee) -> None:
    employee.annual_salary_usd = to_usd(employee.annual_salary, employee.country)


class SalaryChange(Base):
    __tablename__ = "salary_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    previous_salary: Mapped[int] = mapped_column(Integer)
    new_salary: Mapped[int] = mapped_column(Integer)
    previous_currency: Mapped[str] = mapped_column(String(3))
    new_currency: Mapped[str] = mapped_column(String(3))
    reason: Mapped[str | None] = mapped_column(String(255))
    # When the new salary applies (may be backdated), as opposed to when it was recorded.
    effective_date: Mapped[date] = mapped_column(Date)
    changed_by: Mapped[str] = mapped_column(String(120))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    employee: Mapped[Employee] = relationship(back_populates="salary_changes")

    __table_args__ = (
        # History is read newest-effective-first per employee.
        Index(
            "ix_salary_changes_employee_effective",
            "employee_id",
            "effective_date",
            "changed_at",
            "id",
        ),
    )
