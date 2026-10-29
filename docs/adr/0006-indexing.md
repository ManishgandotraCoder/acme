# 0006 — Index every read path, verified by query-plan tests

**Status:** Accepted

## Context
HR browses, filters, sorts and searches far more than they write. Profiling every read path
on a 200k-employee database (20× today's size, then SQLite) showed 12 of 16 paths doing full
table scans or in-memory sorts:

- search used `LIKE '%term%'`, which no B-tree index can serve;
- lookup by email wrapped the column in `lower()`, bypassing the unique index; this runs on
  **every create/update** for the duplicate check;
- sorting by salary across currencies used a `CASE` expression, which can't be indexed;
- filtered lists and insights found rows by index but then sorted or grouped in memory.

## Decision
(Originally implemented on SQLite; updated for PostgreSQL in [ADR 0007](0007-postgresql.md).)

1. **List indexes end in `(sort column, id)`**: `(full_name, id)`, `(annual_salary_usd, id)`,
   `(hire_date, id)`, `(country, full_name, id)`, `(department, full_name, id)` and
   `(job_title, full_name, id)`. The repository always breaks ties by `id` for stable paging.
   Postgres (unlike SQLite) doesn't append the row id to indexes, so without `id` every page
   needed an extra sort.
2. **Covering indexes for insights**: `(country, annual_salary, id)`,
   `(country, job_title, annual_salary)`, `(department, country, annual_salary)` and
   `(country, department, annual_salary)`. GROUP BY, aggregates and the
   `percentile_cont` median read only the index.
3. **Stored `annual_salary_usd` column**, kept in sync by ORM `before_insert` /
   `before_update` events and set explicitly by bulk seeding. With a country filter the sort
   uses the local salary instead: one country means one currency, so the order is the same,
   it's exact, and it walks `(country, annual_salary, id)`.
4. **Emails stored lower-case**, so lookups are plain equality on the unique index.
5. **Substring search**: `pg_trgm` GIN indexes on `full_name` and `email` serve
   `ILIKE '%term%'` (combined with a BitmapOr); `%` and `_` typed by users are escaped.
6. **Salary history** index `(employee_id, changed_at, id)` serves newest-first reads.
7. **`tests/unit/test_query_plans.py`** runs the real repository and service calls and fails
   if any plan needs a table scan or a sort. The planner's *choice* depends on table size
   (on 300 test rows a table scan is legitimately cheapest), so the test asks a
   size-independent question: with `enable_seqscan` and `enable_sort` off, Postgres still
   uses a disabled operation only when no index path exists. Search may sort its matches.

## Results (200k employees, median of 7 runs)

| Read path | SQLite before | SQLite after | PostgreSQL |
|---|---:|---:|---:|
| Search "patel" | 162 ms | 4 ms | 5 ms |
| Get by email | 57 ms | 0.1 ms | 0.8 ms |
| Sort by salary (USD) | 24 ms | 0.8 ms | 9 ms |
| Country filter + salary sort | 13 ms | 1.1 ms | 3 ms |
| Sort by hire date | 12 ms | 0.8 ms | 11 ms |
| Country / department / job title filter + name sort | 11 / 10 / 3 ms | 1.1 / 0.7 / 0.4 ms | 3 / 3 / 2 ms |
| Insights: summary / departments / job titles | 67 / 128 / 12 ms | 7 / 10 / 1 ms | 9 / 11 / 3 ms |
| Insights: by country (incl. median) | 239 ms | 96 ms | 18 ms |

PostgreSQL figures include a network round trip to the database and the page's
`COUNT(*)` (an index-only scan over 200k rows, ~5 ms); every row-returning query is an
ordered index walk.

## Consequences
- ✅ Every list, lookup and insight query stays in single-digit ms at 20× today's data.
- ✅ Regressions are caught in CI, not in production.
- ❌ Writes maintain 13 indexes: seeding 10k rows takes 1.2 s on PostgreSQL (target < 5 s).
  Acceptable for a read-heavy tool.
- ❌ The total count is recomputed on every page (~5 ms at 200k). At millions of rows,
  switch to an estimated count or keyset pagination.
- ❌ Filter combinations (e.g. department + salary sort) still sort their filtered subset in
  memory. One index per combination isn't worth the write cost at this scale.
- ⚠️ If the FX table changes, write a migration that recomputes `annual_salary_usd`.
