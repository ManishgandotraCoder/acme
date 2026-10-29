"""initial postgres schema

Squashes the earlier SQLite-era migrations (never deployed) into one PostgreSQL baseline
(ADR 0007). Indexes are explained in ADR 0006.

Revision ID: 417f48fa0e2e
Revises:
Create Date: 2026-10-29 20:45:58.335473

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "417f48fa0e2e"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Trigram operator classes for the substring-search GIN indexes below.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("job_title", sa.String(length=80), nullable=False),
        sa.Column("department", sa.String(length=80), nullable=False),
        sa.Column("country", sa.String(length=60), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("annual_salary", sa.Integer(), nullable=False),
        sa.Column("annual_salary_usd", sa.Integer(), nullable=False),
        sa.Column("hire_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(
        "ix_employees_annual_salary_usd_id", "employees", ["annual_salary_usd", "id"], unique=False
    )
    op.create_index(
        "ix_employees_country_department_salary",
        "employees",
        ["country", "department", "annual_salary"],
        unique=False,
    )
    op.create_index(
        "ix_employees_country_full_name_id",
        "employees",
        ["country", "full_name", "id"],
        unique=False,
    )
    op.create_index(
        "ix_employees_country_job_title_salary",
        "employees",
        ["country", "job_title", "annual_salary"],
        unique=False,
    )
    op.create_index(
        "ix_employees_country_salary_id",
        "employees",
        ["country", "annual_salary", "id"],
        unique=False,
    )
    op.create_index(
        "ix_employees_department_country_salary",
        "employees",
        ["department", "country", "annual_salary"],
        unique=False,
    )
    op.create_index(
        "ix_employees_department_full_name_id",
        "employees",
        ["department", "full_name", "id"],
        unique=False,
    )
    op.create_index(
        "ix_employees_email_trgm",
        "employees",
        ["email"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"email": "gin_trgm_ops"},
    )
    op.create_index("ix_employees_full_name_id", "employees", ["full_name", "id"], unique=False)
    op.create_index(
        "ix_employees_full_name_trgm",
        "employees",
        ["full_name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"full_name": "gin_trgm_ops"},
    )
    op.create_index("ix_employees_hire_date_id", "employees", ["hire_date", "id"], unique=False)
    op.create_index(
        "ix_employees_job_title_full_name_id",
        "employees",
        ["job_title", "full_name", "id"],
        unique=False,
    )
    op.create_table(
        "salary_changes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("previous_salary", sa.Integer(), nullable=False),
        sa.Column("new_salary", sa.Integer(), nullable=False),
        sa.Column("previous_currency", sa.String(length=3), nullable=False),
        sa.Column("new_currency", sa.String(length=3), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_salary_changes_employee_changed_at",
        "salary_changes",
        ["employee_id", "changed_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema. pg_trgm is left installed: other objects in the database may use it."""
    op.drop_index("ix_salary_changes_employee_changed_at", table_name="salary_changes")
    op.drop_table("salary_changes")
    op.drop_index("ix_employees_job_title_full_name_id", table_name="employees")
    op.drop_index("ix_employees_hire_date_id", table_name="employees")
    op.drop_index(
        "ix_employees_full_name_trgm",
        table_name="employees",
        postgresql_using="gin",
        postgresql_ops={"full_name": "gin_trgm_ops"},
    )
    op.drop_index("ix_employees_full_name_id", table_name="employees")
    op.drop_index(
        "ix_employees_email_trgm",
        table_name="employees",
        postgresql_using="gin",
        postgresql_ops={"email": "gin_trgm_ops"},
    )
    op.drop_index("ix_employees_department_full_name_id", table_name="employees")
    op.drop_index("ix_employees_department_country_salary", table_name="employees")
    op.drop_index("ix_employees_country_salary_id", table_name="employees")
    op.drop_index("ix_employees_country_job_title_salary", table_name="employees")
    op.drop_index("ix_employees_country_full_name_id", table_name="employees")
    op.drop_index("ix_employees_country_department_salary", table_name="employees")
    op.drop_index("ix_employees_annual_salary_usd_id", table_name="employees")
    op.drop_table("employees")
