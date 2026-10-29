"""index level and currency filters

Directory filters added with job levels; same (filter, sort column, id) shape as the other
list indexes (ADR 0006), found missing by tests/unit/test_query_plans.py.

Revision ID: 012b0fc7b34c
Revises: 4f40d31970f9
Create Date: 2026-10-29 21:10:53.085207

"""

from collections.abc import Sequence

from alembic import op

revision: str = "012b0fc7b34c"
down_revision: str | Sequence[str] | None = "4f40d31970f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_employees_currency_full_name_id",
        "employees",
        ["currency", "full_name", "id"],
        unique=False,
    )
    op.create_index(
        "ix_employees_job_level_full_name_id",
        "employees",
        ["job_level", "full_name", "id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_employees_job_level_full_name_id", table_name="employees")
    op.drop_index("ix_employees_currency_full_name_id", table_name="employees")
