"""Full-text index for employee search (SQLite FTS5, trigram tokenizer).

``LIKE '%term%'`` can't use a B-tree index, so search would read every row. A trigram FTS5
table indexes every 3-character slice of name and email, which makes case-insensitive
substring search an index lookup. Triggers keep it in sync with ``employees`` on every write
path (ORM, bulk inserts, raw SQL). Terms shorter than 3 characters fall back to ``LIKE``.

Other databases: the repository uses ``ILIKE``; on Postgres, add a ``pg_trgm`` GIN index.
Gotcha: an Alembic *batch* operation on ``employees`` (SQLite table rebuild) drops these
triggers. Re-run ``CREATE_STATEMENTS`` after such a migration.
"""

from app.core.database import search_table_name

TABLE = search_table_name("employees")
MIN_TERM_LENGTH = 3  # trigram tokenizer needs at least one full trigram

CREATE_STATEMENTS = (
    f"CREATE VIRTUAL TABLE {TABLE} USING fts5("
    "full_name, email, content='employees', content_rowid='id', tokenize='trigram')",
    f"CREATE TRIGGER {TABLE}_ai AFTER INSERT ON employees BEGIN "
    f"INSERT INTO {TABLE}(rowid, full_name, email) VALUES (new.id, new.full_name, new.email); END",
    f"CREATE TRIGGER {TABLE}_ad AFTER DELETE ON employees BEGIN "
    f"INSERT INTO {TABLE}({TABLE}, rowid, full_name, email) "
    "VALUES ('delete', old.id, old.full_name, old.email); END",
    f"CREATE TRIGGER {TABLE}_au AFTER UPDATE OF full_name, email ON employees BEGIN "
    f"INSERT INTO {TABLE}({TABLE}, rowid, full_name, email) "
    "VALUES ('delete', old.id, old.full_name, old.email); "
    f"INSERT INTO {TABLE}(rowid, full_name, email) VALUES (new.id, new.full_name, new.email); END",
    # Index rows that already exist (no-op on an empty table).
    f"INSERT INTO {TABLE}({TABLE}) VALUES ('rebuild')",
)

DROP_STATEMENTS = (
    f"DROP TRIGGER IF EXISTS {TABLE}_au",
    f"DROP TRIGGER IF EXISTS {TABLE}_ad",
    f"DROP TRIGGER IF EXISTS {TABLE}_ai",
    f"DROP TABLE IF EXISTS {TABLE}",
)


def match_expression(term: str) -> str:
    """Quote the user's term as one FTS5 phrase, so operators in input are taken literally."""
    return '"' + term.replace('"', '""') + '"'
