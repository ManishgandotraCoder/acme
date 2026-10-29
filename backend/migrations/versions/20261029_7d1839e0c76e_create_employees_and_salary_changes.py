"""create employees and salary changes

Revision ID: 7d1839e0c76e
Revises:
Create Date: 2026-10-29 19:03:00.949167

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7d1839e0c76e"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
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
        sa.Column("hire_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_employees_annual_salary"), ["annual_salary"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_employees_country"), ["country"], unique=False)
        batch_op.create_index(
            "ix_employees_country_job_title", ["country", "job_title"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_employees_department"), ["department"], unique=False)
        batch_op.create_index(batch_op.f("ix_employees_full_name"), ["full_name"], unique=False)
        batch_op.create_index(batch_op.f("ix_employees_job_title"), ["job_title"], unique=False)

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
    with op.batch_alter_table("salary_changes", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_salary_changes_employee_id"), ["employee_id"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("salary_changes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_salary_changes_employee_id"))

    op.drop_table("salary_changes")
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_employees_job_title"))
        batch_op.drop_index(batch_op.f("ix_employees_full_name"))
        batch_op.drop_index(batch_op.f("ix_employees_department"))
        batch_op.drop_index("ix_employees_country_job_title")
        batch_op.drop_index(batch_op.f("ix_employees_country"))
        batch_op.drop_index(batch_op.f("ix_employees_annual_salary"))

    op.drop_table("employees")
