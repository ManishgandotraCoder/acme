# Decisions, trade-offs and performance

## Key decisions

The decisions that shape the codebase are written up as [ADRs](adr/README.md); this table
is the quick overview.

| # | Decision | Why | Trade-off accepted |
|---|---|---|---|
| 1 | **Store salaries in local currency**, derive currency from country | That's how contracts and payslips work; HR thinks in local amounts | Every cross-country view must convert — centralised in `shared/countries.py` |
| 2 | **Static, dated FX table** (shown in the UI as "as of 2026-10-01") | Reports are reproducible and tests deterministic | Rates drift; one module to swap for a live rates provider |
| 3 | **Convert after grouping by country** in insights | Never `SUM` mixed currencies | Department totals need a `(department, country)` group-by then a fold in Python — trivial at this scale |
| 4 | **Salary sort ranks by USD equivalent** (stored, indexed `annual_salary_usd`; [ADR 0006](adr/0006-indexing.md)) | "Highest paid" must compare like with like (bug found in smoke test: JPY salaries sorted first) | Derived column must be recomputed if FX rates change |
| 5 | **Changing to a different-currency country requires a new salary** | Otherwise 2,400,000 INR silently becomes 2,400,000 EUR | One extra field for HR in a rare flow |
| 6 | **Salary history as an append-only table**, written by the service | Audit trail is the #1 reason to leave spreadsheets | Only salary/currency changes are audited, not every field |
| 7 | **Integer salaries (whole units)** | Annual salaries are never fractional; avoids float/Decimal issues in SQLite aggregates | Can't represent cents (not needed) |
| 8 | **LLM classifies intent only; answers are templated from SQL results** | A hallucinated pay figure is worse than no answer; no text-to-SQL means no injection surface | Can only answer the 4 supported question shapes (+ variations); unsupported questions get a helpful hint |
| 9 | **Verify the LLM's entities against the question text** | Found empirically: llama3.2 drops entities and invents filters (see AI_USAGE.md) | Synonyms the model maps ("devs" → Software Engineer) are dropped unless grounded |
| 10 | **SQLite** | Zero-ops, file-based, ample for 10k rows; requirement allowed it | Single writer; Postgres is a `DATABASE_URL` change (repository layer has no SQLite-specific code besides pragmas) |
| 11 | **Modular monolith** (core / shared / modules), boundaries enforced by tests ([ADR 0001](adr/0001-modular-monolith.md)) | A feature lives in one folder; coupling is a reviewed decision; extractable later | More structure than a single-file app; microservices rejected as overkill |
| 12 | **App factory with injected LLM** | Tests are hermetic and fast; Ollama outages degrade one feature, not the app | — |
| 13 | **Single deployable container** (API serves built UI) | Simplest possible deployment & no CORS in prod | UI and API scale together (fine for an internal HR tool) |
| 14 | **Mantine** component library | Accessible, complete (tables, forms, charts, notifications), little CSS to write | Larger bundle — mitigated by route-level code splitting |
| 16 | **Domain error categories** (NotFound / Conflict / BusinessRule / ServiceUnavailable) mapped to HTTP once | Services stay HTTP-free; new errors need no infrastructure change | — |
| 17 | **Alembic migrations + drift test** ([ADR 0004](adr/0004-sqlite-with-alembic.md)) | Schema can evolve with data in place; models can't silently diverge | One extra step on deploy (automated in the container) |
| 18 | **Request IDs + access logs, liveness/readiness endpoints** | Minimum needed to debug production and run behind a load balancer | — |
| 19 | **Index every read path** + query-plan tests ([ADR 0006](adr/0006-indexing.md)) | 4–40× faster reads at 200k rows; regressions caught in CI | Slower bulk writes (10k seed 0.12 s → 0.81 s) |
| 15 | **Offset pagination** (page/page_size ≤ 100) | Users jump to page N; data set is small | Deep offsets would be slow at millions of rows (keyset pagination then) |

## Deliberately not built
See the table in [REQUIREMENTS.md](REQUIREMENTS.md#deliberately-left-out-and-why) — auth,
live FX, payroll/tax, Excel import, multi-tenancy.

## Performance

Measured on a laptop (Apple Silicon) with 10,000 seeded employees, warm process:

| Operation | Time | Target |
|---|---|---|
| Seed 10,000 employees (bulk Core insert, one transaction, 10 indexes + FTS) | **0.81 s** | < 5 s |
| `GET /api/employees` page 1 | 1.8 ms | < 200 ms |
| Search + filter + salary sort | 3.9 ms | < 200 ms |
| `GET /api/insights/summary` | 2.0 ms | < 200 ms |
| `GET /api/insights/countries` (incl. medians) | 7.7 ms | < 200 ms |
| `GET /api/insights/departments` | 4.1 ms | < 200 ms |
| `POST /api/ask` (llama3.2, local) | 0.3 – 2 s | dominated by the model |

How:
- Indexes on every filter/sort column, composite `(country, job_title)`.
- Aggregates (`COUNT/MIN/MAX/AVG/SUM`) computed in SQL, not by loading rows.
- Median needs ordered values: one ordered scan of `(country, salary)` — 10k integers.
- SQLite WAL mode for concurrent reads during writes.
- Frontend: `keepPreviousData` keeps the table steady while paging; search is debounced
  (300 ms); routes are code-split.

**When it would need to change:** at ~1M employees or many concurrent HR users — move to
Postgres (`percentile_cont` for medians), keyset pagination, and cache insight endpoints
(invalidated on write).
