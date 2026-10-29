# ACME Salary Management

Web application for ACME's HR Manager to manage salary data for 10,000 employees across
10 countries and answer "how do we pay people?" questions, replacing spreadsheets.

**Stack:** Python 3.12 · FastAPI on uvicorn · SQLAlchemy 2 + SQLite + Alembic ·
React 19 + TypeScript · Mantine · TanStack Query · Ollama (local LLM) · pytest ·
Vitest + Testing Library · Docker · GitHub Actions

| Read this | For |
|---|---|
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | Goal, scope, what's deliberately left out (written before any code) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Modules, boundaries, data model, request and AI flows |
| [docs/adr/](docs/adr/README.md) | Architecture Decision Records: the *why* behind key choices |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Trade-off table and measured performance |
| [docs/AI_USAGE.md](docs/AI_USAGE.md) | How AI was used to build this, and where it was wrong |
| [CLAUDE.md](CLAUDE.md) | Standing instructions given to the AI coding agent |
| [docs/ASSIGNMENT.md](docs/ASSIGNMENT.md) | Original brief |

## What the HR manager can do

- **Employee directory (home page):** search 10k employees by name/email; filter by country,
  department and job title; sort (salary sorts compare in USD terms); paginate.
- **Add / edit / remove employees,** with the same validation in the browser and on the server.
- **Salary history:** every salary or currency change is recorded with a reason.
- **Pay insights** (button on the home page → `/insights`): headline org numbers; per-country
  min/median/average/max (local currency and USD); pay by job title within a country; pay by
  department.
- **Pay assistant chat** (bottom-right on every page): "What do data analysts earn in Germany?"
  A local Ollama model interprets the question; **every number comes from the database**, never
  from the model. The conversation persists while you move between pages.

## Quick start

```bash
make setup        # install backend + frontend deps, git hooks
make db-reset     # migrate + seed 10,000 employees
make dev-api      # http://localhost:8000/docs
make dev-web      # http://localhost:5173
```
Prerequisites: Python 3.12 + [uv](https://docs.astral.sh/uv/), Node 22. For the pay assistant:
[Ollama](https://ollama.com) with `ollama pull llama3.2`. Without it everything else works,
and the chat explains that the assistant is unavailable.

**Docker (everything, including Ollama):** `make docker-up` → http://localhost:8000.
The container runs migrations, seeds on first boot only, then serves the UI and the API.

Run `make help` for all tasks. Configuration: `SALARY_*` env vars, see
[backend/.env.example](backend/.env.example).

## Quality

```bash
make check        # what CI runs: lint + types + all tests
```

| | Backend | Frontend |
|---|---|---|
| Tests | 114 in ~0.6 s, 97% coverage | 26 in ~3 s |
| Static checks | ruff (lint + format) | ESLint, `tsc --strict` |

- **Deterministic:** in-memory SQLite per test, seeded RNG, fake LLM, mocked HTTP. No network.
- **Architecture tests** enforce module boundaries ([ADR 0001](docs/adr/0001-modular-monolith.md)).
- **Migration drift test:** models and Alembic migrations can't diverge.
- Warnings fail the backend suite. Pre-commit hooks and
  [CI](.github/workflows/ci.yml) run lint, tests, build and the Docker image.

## Repository layout

```
backend/
  app/
    main.py            composition root
    core/              infrastructure: config, database, errors→HTTP, logging, ops
    shared/            shared kernel: countries, currencies, FX
    modules/
      employees/       CRUD, search, salary audit trail
      insights/        pay analytics (read model)
      assistant/       plain-English questions: prompt → intent → answers
    seed/              deterministic 10k generator
  migrations/          Alembic
  tests/               unit/<module>, unit/core, architecture, api
frontend/src/
  app/                 shell, routes, providers
  shared/              HTTP client, formatting
  features/            employees · insights · assistant (api, types, hooks, components)
docs/                  requirements, architecture, ADRs, decisions, AI usage
```

## How it was built
Test-first, in small commits. `git log --oneline --reverse` reads as the story:
requirements → domain → persistence → services → AI → HTTP → seed → UI → deployment →
restructuring into a modular monolith. `fix:` commits record bugs found by running the real
system (LLM entity hallucination, cross-currency sorting), each pinned by a regression test.
