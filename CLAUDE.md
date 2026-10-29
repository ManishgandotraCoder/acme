# Instructions for AI coding agents

Standing instructions for Claude Code (or any agent) working in this repo. They encode
lessons learned while building it — see docs/AI_USAGE.md.

## Workflow
- **TDD, always.** Write or change the test first, run it and see it fail for the right
  reason, then implement the minimum to pass. Bug fixes start with a regression test.
- **Run checks before every commit:** `make check` (lint, types, all tests). Never commit
  red. Shell pipelines must use `set -o pipefail` so a failing command is not masked by
  `| tail`.
- **Small, incremental commits** with Conventional Commit prefixes
  (`feat`, `fix`, `refactor`, `test`, `docs`, `build`, `ci`, `perf`, `chore`) and a body
  explaining *why*. Pure moves/refactors go in their own commits, separate from behaviour.
- **Verify against the real system**, not only unit tests: for UI/API changes run the app;
  for LLM changes ask real questions through Ollama (`make dev-api`, then `POST /api/ask`).

## Architecture rules (enforced by tests/unit/test_architecture.py)
- `app/core` = infrastructure, `app/shared` = shared kernel; neither imports `app/modules`.
- Each `app/modules/<name>` owns its models, schemas, repository/service, router, errors.
  Cross-module imports must be declared in `ALLOWED_MODULE_DEPENDENCIES`.
- Services raise `app.core.errors` subclasses (NotFound / Conflict / BusinessRule /
  ServiceUnavailable); never raise `HTTPException` outside routers.
- Services own the transaction (`commit`); repositories only build queries.
- Schema changes require an Alembic migration: `make migration m="..."`.
  `tests/unit/core/test_migrations.py` fails on model/migration drift.
- Frontend: `features/<name>` owns `api.ts`, `types.ts` (mirrors backend schemas), hooks,
  components. Shared code lives in `shared/`. Import across folders with `@/`.

## Domain rules that are easy to get wrong
- Salaries are stored in **local currency**. Never sum, average or sort across countries
  without converting via `app/shared/countries.py`.
- Changing an employee to a country with a different currency requires a new salary.
- Every salary/currency change writes a `SalaryChange` row.

## AI feature rules
- The LLM only classifies a question into a `QueryIntent`. It must never produce numbers,
  SQL, or free-text answers. Answers are templated from database results.
- Entities from the model are untrusted: keep them only if grounded in the question
  (`app/modules/assistant/intent.py`). Add a regression test for every new failure mode.

## Tests
- Fast and deterministic: in-memory SQLite, seeded RNG, fake LLM, mocked HTTP. No network.
- Warnings are errors in the backend suite.
- Name tests as behaviours (`test_moving_to_a_different_currency_requires_a_new_salary`).
