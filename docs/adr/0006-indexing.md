# 0006 — Index every read path, verified by query-plan tests

**Status:** Accepted

## Context
HR browses, filters, sorts and searches far more than they write. Profiling every read path
with `EXPLAIN QUERY PLAN` on a 200k-employee database (20× today's size) showed 12 of 16
paths doing full table scans or in-memory sorts:

- search used `LIKE '%term%'`, which no B-tree index can serve;
- lookup by email wrapped the column in `lower()`, bypassing the unique index; this runs on
  **every create/update** for the duplicate check;
- sorting by salary across currencies used a `CASE` expression, which can't be indexed;
- filtered lists and insights found rows by index but then sorted or grouped in memory.

## Decision
1. **Composite indexes end in the sort or aggregate column:** `(country, full_name)`,
   `(department, full_name)` and `(job_title, full_name)` for filtered lists;
   `(country, annual_salary)`, `(country, job_title, annual_salary)`,
   `(department, country, annual_salary)` and `(country, department, annual_salary)` as
   covering indexes for insights. Single-column indexes made redundant by these were dropped.
2. **Stored `annual_salary_usd` column** (indexed), kept in sync by ORM `before_insert` /
   `before_update` events and set explicitly by bulk seeding. With a country filter the sort
   uses the local salary instead: one country means one currency, so the order is the same,
   it's exact, and it walks `(country, annual_salary)`.
3. **Emails stored lower-case**, so lookups are plain equality on the unique index.
4. **FTS5 trigram index** (`employees_search`) for substring search on name and email,
   synced by triggers. User input is always quoted as one phrase. Terms under 3 characters
   fall back to `LIKE`. Non-SQLite databases use `ILIKE` (add `pg_trgm` GIN on Postgres).
5. **Salary history** index `(employee_id, changed_at, id)` serves newest-first reads.
6. **`tests/unit/test_query_plans.py`** runs the real repository and service calls and
   fails if any plan contains a table scan or an in-memory sort (search may sort its small
   match set).

## Results (200k employees, median of 5 runs)

| Read path | Before | After |
|---|---:|---:|
| Search "patel" | 162 ms | 4 ms |
| Get by email | 57 ms | 0.1 ms |
| Sort by salary (USD) | 24 ms | 0.8 ms |
| Country filter + salary sort | 13 ms | 1.1 ms |
| Sort by hire date | 12 ms | 0.8 ms |
| Country / department / job title filter + name sort | 11 / 10 / 3 ms | 1.1 / 0.7 / 0.4 ms |
| Insights: summary / departments / job titles | 67 / 128 / 12 ms | 7 / 10 / 1 ms |
| Insights: by country (incl. median) | 239 ms | 96 ms |

## Consequences
- ✅ Every list, lookup and insight query stays in single-digit ms at 20× today's data.
- ✅ Regressions are caught in CI, not in production.
- ❌ Writes maintain 10 indexes plus the search index: seeding 10k rows went from 0.12 s to
  0.81 s (target < 5 s). Acceptable for a read-heavy tool.
- ❌ Filter combinations (e.g. department + salary sort) still sort their filtered subset in
  memory. One index per combination isn't worth the write cost at this scale.
- ⚠️ The country median still sends every salary to Python (96 ms at 200k). On Postgres,
  use `percentile_cont`.
- ⚠️ An Alembic **batch** operation on `employees` rebuilds the table and drops the search
  triggers. Re-create them in the same migration (see the `index read paths` migration).
- ⚠️ If the FX table changes, write a migration that recomputes `annual_salary_usd`.
