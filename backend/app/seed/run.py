"""Seed the database: ``python -m app.seed.run --count 10000 --reset``.

Expects a migrated schema (``alembic upgrade head``).
"""

import argparse
import random
import time
from datetime import UTC, datetime
from datetime import time as clock

from sqlalchemy import delete, exists, insert, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import make_engine, make_session_factory
from app.modules.employees.models import Employee, SalaryChange
from app.seed.generator import generate_employees, generate_salary_history, load_names


def seed_database(
    session: Session,
    *,
    count: int,
    seed: int = 42,
    reset: bool = False,
    only_if_empty: bool = False,
) -> int:
    if only_if_empty and session.scalar(select(exists().select_from(Employee))):
        return 0
    if reset:
        session.execute(delete(SalaryChange))
        session.execute(delete(Employee))
    first, last = load_names()
    rng = random.Random(seed)
    rows = generate_employees(count, rng, first, last)
    history = generate_salary_history(rows, rng)

    # Core bulk inserts in one transaction: ~10x faster than adding ORM objects one by one.
    # sort_by_parameter_order returns ids in input order, to link each history row.
    ids = session.scalars(
        insert(Employee).returning(Employee.id, sort_by_parameter_order=True), rows
    ).all()
    if history:
        session.execute(
            insert(SalaryChange),
            [
                {
                    **{k: v for k, v in change.items() if k != "employee_index"},
                    "employee_id": ids[change["employee_index"]],
                    "changed_at": datetime.combine(change["effective_date"], clock(9), UTC),
                }
                for change in history
            ],
        )
    session.commit()
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--reset", action="store_true", help="delete existing employees first")
    parser.add_argument(
        "--if-empty", action="store_true", help="only seed when there are no employees yet"
    )
    args = parser.parse_args()

    engine = make_engine(get_settings().database_url)
    started = time.perf_counter()
    with make_session_factory(engine)() as session:
        inserted = seed_database(
            session, count=args.count, seed=args.seed, reset=args.reset, only_if_empty=args.if_empty
        )
    print(f"Seeded {inserted:,} employees in {time.perf_counter() - started:.2f}s")


if __name__ == "__main__":
    main()
