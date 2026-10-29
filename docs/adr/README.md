# Architecture Decision Records

Short records of decisions that shape the codebase: context, decision, consequences.
New decisions get the next number; superseded ones are marked, never deleted.

| # | Decision | Status |
|---|---|---|
| [0001](0001-modular-monolith.md) | Modular monolith with enforced module boundaries | Accepted |
| [0002](0002-salaries-in-local-currency.md) | Store salaries in local currency; convert via one FX table | Accepted |
| [0003](0003-llm-classifies-intent-only.md) | LLM classifies intent only; answers come from the database | Accepted |
| [0004](0004-sqlite-with-alembic.md) | SQLite with Alembic migrations, Postgres-ready | Accepted |
| [0005](0005-single-container-deployment.md) | Single container serving API and UI | Accepted |
| [0006](0006-indexing.md) | Index every read path, verified by query-plan tests | Accepted |
