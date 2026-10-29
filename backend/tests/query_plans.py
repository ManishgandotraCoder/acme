"""Capture the SQL a callable emits and return PostgreSQL's plan nodes for each statement.

The planner's *choice* depends on table size: on 300 test rows a table scan or a small sort is
legitimately cheapest, while at production scale the index wins. So these tests ask a
size-independent question instead: "does an index path exist that avoids a table scan and a
sort?" With ``enable_seqscan``/``enable_sort`` off, Postgres still uses a disabled operation
only when it has no alternative, so any Seq Scan or Sort left in the plan is a missing index.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass

from sqlalchemy import event, text
from sqlalchemy.orm import Session

TABLES = {"employees", "salary_changes"}


@dataclass(frozen=True)
class PlanNode:
    node_type: str
    relation: str | None
    index: str | None

    def __str__(self) -> str:
        on = f" on {self.relation}" if self.relation else ""
        using = f" using {self.index}" if self.index else ""
        return f"{self.node_type}{on}{using}"


def query_plans(
    session: Session, action: Callable[[], object], *, allow_sort: bool = False
) -> list[PlanNode]:
    statements: list[tuple[str, object]] = []

    def capture(conn, cursor, statement, params, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append((statement, params))

    engine = session.get_bind().engine
    event.listen(engine, "before_cursor_execute", capture)
    try:
        action()
    finally:
        event.remove(engine, "before_cursor_execute", capture)

    connection = session.connection()
    connection.execute(text("SET LOCAL enable_seqscan = off"))
    connection.execute(text(f"SET LOCAL enable_sort = {'on' if allow_sort else 'off'}"))
    nodes: list[PlanNode] = []
    for sql, params in statements:
        [[plan]] = connection.exec_driver_sql(f"EXPLAIN (FORMAT JSON) {sql}", params).all()
        nodes.extend(_walk(plan[0]["Plan"]))
    return nodes


def _walk(node: dict) -> Iterator[PlanNode]:
    yield PlanNode(node["Node Type"], node.get("Relation Name"), node.get("Index Name"))
    for child in node.get("Plans", []):
        yield from _walk(child)


def table_scans(plans: list[PlanNode]) -> list[str]:
    return [str(n) for n in plans if n.node_type == "Seq Scan" and n.relation in TABLES]


def sorts(plans: list[PlanNode]) -> list[str]:
    return [str(n) for n in plans if n.node_type in ("Sort", "Incremental Sort")]
