"""index read paths

Every read path gets an index (docs/adr/0006-indexing.md):
- annual_salary_usd: stored, indexed USD salary for cross-currency sorting
- composite indexes for filtered lists and covering indexes for insights
- FTS5 trigram index for substring search on name/email
- emails normalised to lower case so lookups can use the unique index

Revision ID: e962ac86377d
Revises: 7d1839e0c76e
Create Date: 2026-10-29 20:07:39.349476

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e962ac86377d"
down_revision: str | Sequence[str] | None = "7d1839e0c76e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Frozen copy of app/shared/countries.py rates at the time of this migration, so the
# backfill is reproducible even if the app's FX table changes later.
USD_RATES = {
    "Australia": 0.66,
    "Brazil": 0.18,
    "Canada": 0.73,
    "France": 1.08,
    "Germany": 1.08,
    "India": 0.012,
    "Japan": 0.0067,
    "Singapore": 0.74,
    "United Kingdom": 1.27,
    "United States": 1.0,
}

# Frozen copy of app/modules/employees/search_index.py DDL.
SEARCH_CREATE = (
    "CREATE VIRTUAL TABLE employees_search USING fts5("
    "full_name, email, content='employees', content_rowid='id', tokenize='trigram')",
    "CREATE TRIGGER employees_search_ai AFTER INSERT ON employees BEGIN "
    "INSERT INTO employees_search(rowid, full_name, email) "
    "VALUES (new.id, new.full_name, new.email); END",
    "CREATE TRIGGER employees_search_ad AFTER DELETE ON employees BEGIN "
    "INSERT INTO employees_search(employees_search, rowid, full_name, email) "
    "VALUES ('delete', old.id, old.full_name, old.email); END",
    "CREATE TRIGGER employees_search_au AFTER UPDATE OF full_name, email ON employees BEGIN "
    "INSERT INTO employees_search(employees_search, rowid, full_name, email) "
    "VALUES ('delete', old.id, old.full_name, old.email); "
    "INSERT INTO employees_search(rowid, full_name, email) "
    "VALUES (new.id, new.full_name, new.email); END",
    "INSERT INTO employees_search(employees_search) VALUES ('rebuild')",
)
SEARCH_DROP = (
    "DROP TRIGGER IF EXISTS employees_search_au",
    "DROP TRIGGER IF EXISTS employees_search_ad",
    "DROP TRIGGER IF EXISTS employees_search_ai",
    "DROP TABLE IF EXISTS employees_search",
)

NEW_EMPLOYEE_INDEXES = {
    "ix_employees_annual_salary_usd": ["annual_salary_usd"],
    "ix_employees_hire_date": ["hire_date"],
    "ix_employees_country_full_name": ["country", "full_name"],
    "ix_employees_department_full_name": ["department", "full_name"],
    "ix_employees_job_title_full_name": ["job_title", "full_name"],
    "ix_employees_country_salary": ["country", "annual_salary"],
    "ix_employees_country_job_title_salary": ["country", "job_title", "annual_salary"],
    "ix_employees_department_country_salary": ["department", "country", "annual_salary"],
    "ix_employees_country_department_salary": ["country", "department", "annual_salary"],
}
OLD_EMPLOYEE_INDEXES = {
    "ix_employees_annual_salary": ["annual_salary"],
    "ix_employees_country": ["country"],
    "ix_employees_country_job_title": ["country", "job_title"],
    "ix_employees_department": ["department"],
    "ix_employees_job_title": ["job_title"],
}


def upgrade() -> None:
    # 1. Add the derived column (nullable until backfilled).
    with op.batch_alter_table("employees") as batch_op:
        batch_op.add_column(sa.Column("annual_salary_usd", sa.Integer(), nullable=True))

    # 2. Backfill data the new read paths depend on.
    rate = sa.case(USD_RATES, value=sa.column("country"), else_=1.0)
    employees = sa.table(
        "employees",
        sa.column("annual_salary"),
        sa.column("annual_salary_usd"),
        sa.column("country"),
        sa.column("email"),
    )
    op.execute(
        employees.update().values(
            annual_salary_usd=sa.cast(sa.func.round(sa.column("annual_salary") * rate), sa.Integer),
            email=sa.func.lower(sa.column("email")),
        )
    )

    # 3. Enforce NOT NULL and swap indexes (SQLite rebuilds the table here).
    with op.batch_alter_table("employees") as batch_op:
        batch_op.alter_column("annual_salary_usd", existing_type=sa.Integer(), nullable=False)
        for name in OLD_EMPLOYEE_INDEXES:
            batch_op.drop_index(name)
        for name, columns in NEW_EMPLOYEE_INDEXES.items():
            batch_op.create_index(name, columns, unique=False)

    with op.batch_alter_table("salary_changes") as batch_op:
        batch_op.drop_index("ix_salary_changes_employee_id")
        batch_op.create_index(
            "ix_salary_changes_employee_changed_at", ["employee_id", "changed_at", "id"]
        )

    # 4. Full-text search last: a batch table rebuild would drop its triggers.
    if op.get_bind().dialect.name == "sqlite":
        for statement in SEARCH_CREATE:
            op.execute(statement)


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        for statement in SEARCH_DROP:
            op.execute(statement)

    with op.batch_alter_table("salary_changes") as batch_op:
        batch_op.drop_index("ix_salary_changes_employee_changed_at")
        batch_op.create_index("ix_salary_changes_employee_id", ["employee_id"])

    with op.batch_alter_table("employees") as batch_op:
        for name in NEW_EMPLOYEE_INDEXES:
            batch_op.drop_index(name)
        for name, columns in OLD_EMPLOYEE_INDEXES.items():
            batch_op.create_index(name, columns, unique=False)
        batch_op.drop_column("annual_salary_usd")
