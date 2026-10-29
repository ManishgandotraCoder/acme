"""job level and salary change audit fields

Existing rows are backfilled so the columns can be NOT NULL: employees start at "Mid", and
past salary changes take effect on the day they were recorded, by an unknown author (the app
did not record one before this migration).

Revision ID: 4f40d31970f9
Revises: 417f48fa0e2e
Create Date: 2026-10-29 21:06:54.939524

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4f40d31970f9"
down_revision: str | Sequence[str] | None = "417f48fa0e2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "employees",
        sa.Column("job_level", sa.String(length=20), nullable=False, server_default="Mid"),
    )
    op.alter_column("employees", "job_level", server_default=None)

    op.add_column("salary_changes", sa.Column("effective_date", sa.Date(), nullable=True))
    op.execute("UPDATE salary_changes SET effective_date = changed_at::date")
    op.alter_column("salary_changes", "effective_date", nullable=False)
    op.add_column(
        "salary_changes",
        sa.Column(
            "changed_by",
            sa.String(length=120),
            nullable=False,
            server_default="Unknown (recorded before audit)",
        ),
    )
    op.alter_column("salary_changes", "changed_by", server_default=None)

    op.drop_index("ix_salary_changes_employee_changed_at", table_name="salary_changes")
    op.create_index(
        "ix_salary_changes_employee_effective",
        "salary_changes",
        ["employee_id", "effective_date", "changed_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_salary_changes_employee_effective", table_name="salary_changes")
    op.create_index(
        "ix_salary_changes_employee_changed_at",
        "salary_changes",
        ["employee_id", "changed_at", "id"],
        unique=False,
    )
    op.drop_column("salary_changes", "changed_by")
    op.drop_column("salary_changes", "effective_date")
    op.drop_column("employees", "job_level")
