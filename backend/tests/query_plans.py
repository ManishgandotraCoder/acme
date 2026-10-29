"""Capture the SQL a callable emits and return SQLite's query plan for each statement."""

from collections.abc import Callable

from sqlalchemy import event
from sqlalchemy.orm import Session


def query_plans(session: Session, action: Callable[[], object]) -> list[str]:
    statements: list[tuple[str, object]] = []

    def capture(conn, cursor, statement, params, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append((statement, params))

    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", capture)
    try:
        action()
    finally:
        event.remove(engine, "before_cursor_execute", capture)

    connection = session.connection()
    return [
        row[3]
        for sql, params in statements
        for row in connection.exec_driver_sql(f"EXPLAIN QUERY PLAN {sql}", params)
    ]


def full_scans_and_sorts(plans: list[str]) -> list[str]:
    """Plan steps that read a whole table without an index, or sort in memory."""
    return [
        step
        for step in plans
        if "TEMP B-TREE" in step
        or (step.startswith("SCAN ") and " INDEX " not in step and "VIRTUAL TABLE" not in step)
    ]
