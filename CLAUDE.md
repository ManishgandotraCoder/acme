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
  PermissionDenied / ServiceUnavailable); never raise `HTTPException` outside routers.
- Who is acting comes from `app/core/actor.py` (`ActorDep`); services receive the actor
  explicitly. Never read identity or permissions anywhere else.
- Services own the transaction (`commit`); repositories only build queries.
- New or changed queries must be index-backed: add the read path to
  `tests/unit/test_query_plans.py` (fails on table scans / sorts). List indexes end in
  `(sort column, id)` because the repository breaks ties by id. See ADR 0006.
- `annual_salary_usd` is derived. Never set it by hand in ORM code (model events do it);
  bulk Core inserts must set it. Emails are stored lower-case.
- Schema changes require an Alembic migration: `make migration m="..."`.
  `tests/unit/core/test_migrations.py` fails on model/migration drift.
- Frontend: `features/<name>` owns `api.ts`, `types.ts` (mirrors backend schemas), hooks,
  components. Shared code lives in `shared/`. Import across folders with `@/`.

## Domain rules that are easy to get wrong
- Salaries are stored in **local currency**. Never sum, average or sort across countries
  without converting via `app/shared/countries.py`.
- Changing an employee to a country with a different currency requires a new salary.
- Every salary/currency change writes a `SalaryChange` row, with an effective date and the
  acting user (`changed_by`).
- Comparing pay across groups must compare like with like: level gaps within the same job title
  and country; outliers against peers with the same title, level and country. An org-wide
  median per level mostly measures the country mix.
- Results that name individuals need `view_individual_pay`; without it, pay for groups under
  3 people is hidden (`MIN_GROUP_SIZE` in `assistant/answers.py`).

## AI feature rules
- The LLM only selects an allow-listed operation into a `QueryIntent`. It must never produce
  numbers, SQL, or answer text, and never sees salary data. Answers are templated from database
  results (ADR 0008). No RAG unless documents come into scope.
- A new question type = an insights method (+ query-plan test) + a template in
  `assistant/answers.py` + a prompt line + a question in `tests/benchmark/questions.py`
  checked against the oracle. After prompt or resolver changes, run `make benchmark-llm`.
- Model providers sit behind `LLMClient`; a provider must never change an answer's numbers.
- Entities from the model are untrusted: keep them only if grounded in the question
  (`app/modules/assistant/intent.py`). Add a regression test for every new failure mode.

## Tests
- Tests run on real PostgreSQL (throwaway container, or `SALARY_TEST_DATABASE_URL`), each in a
  rolled-back transaction. Never hard-code ids: rollbacks don't rewind sequences.
- Query-plan tests disable seq scans, sorts *and incremental sorts*; table bloat from other
  tests changes the planner's choices, so the check must not depend on them.
- The Anthropic SDK (2.x) runs on `httpx2`: fake it with `httpx2.MockTransport`, not `httpx`.
- Deterministic otherwise: seeded RNG, fake LLM, mocked HTTP.
- Warnings are errors in the backend suite.
- Name tests as behaviours (`test_moving_to_a_different_currency_requires_a_new_salary`).
