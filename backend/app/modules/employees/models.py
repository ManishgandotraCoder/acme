from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    job_title: Mapped[str] = mapped_column(String(80), index=True)
    department: Mapped[str] = mapped_column(String(80), index=True)
    country: Mapped[str] = mapped_column(String(60), index=True)
    currency: Mapped[str] = mapped_column(String(3))
    # Whole units of local currency. Annual salaries are never fractional in practice,
    # and integers avoid float rounding in aggregates.
    annual_salary: Mapped[int] = mapped_column(Integer, index=True)
    hire_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    salary_changes: Mapped[list["SalaryChange"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="desc(SalaryChange.changed_at)",
    )

    __table_args__ = (Index("ix_employees_country_job_title", "country", "job_title"),)


class SalaryChange(Base):
    __tablename__ = "salary_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True
    )
    previous_salary: Mapped[int] = mapped_column(Integer)
    new_salary: Mapped[int] = mapped_column(Integer)
    previous_currency: Mapped[str] = mapped_column(String(3))
    new_currency: Mapped[str] = mapped_column(String(3))
    reason: Mapped[str | None] = mapped_column(String(255))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    employee: Mapped[Employee] = relationship(back_populates="salary_changes")
