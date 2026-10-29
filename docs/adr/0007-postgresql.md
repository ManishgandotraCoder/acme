# 0007 — PostgreSQL as the database

**Status:** Accepted. Supersedes [0004](0004-sqlite-with-alembic.md).

## Context
SQLite was chosen for zero-ops local setup (ADR 0004). The application is a multi-user web
app that will be deployed; that and the work in ADR 0006 exposed SQLite's limits:
- a single writer, and the database file is tied to one container's disk;
- substring search needed a SQLite-only FTS5 table kept in sync by triggers, which Alembic
  batch migrations silently drop;
- no `percentile_cont`, so the country median sent every salary to Python;
- tests on SQLite didn't exercise the database production would run.

## Decision
- **PostgreSQL 17** everywhere: local dev (docker compose, port 5433), CI (service
  container), production (`SALARY_DATABASE_URL`). Driver: psycopg 3.
- **Tests run against real Postgres.** A throwaway container is started per test session
  (testcontainers), or `SALARY_TEST_DATABASE_URL` is used (CI). The schema is created once;
  each test runs in a transaction that is rolled back, with `session.commit()` turned into a
  SAVEPOINT. The full suite takes ~3 s.
- **Search:** `pg_trgm` GIN indexes on `full_name` and `email` serve plain
  `ILIKE '%term%'`. User-typed `%` and `_` are escaped. No triggers, no shadow tables.
- **Median in SQL:** `percentile_cont(0.5) WITHIN GROUP (ORDER BY annual_salary)`.
- **One baseline migration.** The two SQLite-era migrations were never deployed, so they
  were squashed into a single PostgreSQL migration (including `CREATE EXTENSION pg_trgm`).
- Local SQLite dev data was copied into Postgres with ids preserved, then the sequences
  were moved past the copied ids.

## Consequences
- ✅ Concurrent writers, a real server to back up and replicate, and one database
  dialect to reason about. The SQLite-only search code and migration workarounds are gone.
- ✅ Tests catch Postgres-specific behaviour. They already caught three things SQLite hid:
  `AVG()` returns `Decimal`; rolled-back tests don't rewind sequences, so tests must not
  assume ids; indexes don't implicitly end in the row id (see ADR 0006).
- ❌ Running the app or the tests locally now needs Docker. `make db-up` and the test
  fixtures start Postgres automatically.
- ❌ Each query crosses the network: list endpoints went from ~1 ms (in-process SQLite) to
  ~2–10 ms at 200k rows. Still far inside the 200 ms budget.
- ⚠️ Rolled-back tests don't reset sequences. Tests must look up ids, never hard-code them.
