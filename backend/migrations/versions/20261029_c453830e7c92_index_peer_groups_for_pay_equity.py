"""index peer groups for pay equity

Like-for-like level gaps and outlier detection group employees by (job title, country,
level) and take the salary median; this index serves that read without a sort (ADR 0006).

Revision ID: c453830e7c92
Revises: 012b0fc7b34c
Create Date: 2026-10-29 21:18:43.937017

"""

from collections.abc import Sequence

from alembic import op

revision: str = "c453830e7c92"
down_revision: str | Sequence[str] | None = "012b0fc7b34c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_employees_title_country_level_salary",
        "employees",
        ["job_title", "country", "job_level", "annual_salary"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_employees_title_country_level_salary", table_name="employees")
