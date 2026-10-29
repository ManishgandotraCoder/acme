# 0004 — SQLite with Alembic migrations, Postgres-ready

**Status:** Accepted

## Context
10k employees, few concurrent writers, a brief that suggests SQLite, and a need for
zero-ops local setup. The schema will change (bonuses, job levels, …) once real data
exists, so `create_all()` is not enough.

## Decision
- SQLite (WAL mode, foreign keys on) via SQLAlchemy 2.0.
- Alembic owns the production schema: `alembic upgrade head` runs at deploy/start. The app
  never changes the schema itself (`auto_create_schema` is for tests only).
- A test upgrades a fresh database and fails on any model/migration drift; batch mode is on
  so SQLite ALTERs work.
- No SQLite-specific SQL in repositories or services.

## Consequences
- ✅ Every list and insight query takes under 10 ms on 10k rows; nothing to operate.
- ✅ Moving to Postgres = change `SALARY_DATABASE_URL`, add a driver, replace the Python
  median with `percentile_cont`.
- ❌ Single writer: fine for one HR team, not for heavy concurrent writes.
