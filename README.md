# ACME Salary Management

Web application for ACME's HR Manager to manage salary data for 10,000 employees across
10 countries and answer "how do we pay people?" questions, replacing spreadsheets. Two core
capabilities: **Salary Management** and **Salary Intelligence** (ask the salary data in plain
English).

**Stack:** Python 3.12 · FastAPI on uvicorn · SQLAlchemy 2 + PostgreSQL 17 + Alembic ·
React 19 + TypeScript · Mantine · TanStack Query · Zustand · Ollama (default) / Claude / OpenAI · pytest ·
Vitest + Testing Library · Docker · GitHub Actions

| Read this | For |
|---|---|
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | Goal, scope, what's deliberately left out (written before any code) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Modules, boundaries, data model, request and AI flows |
| [docs/adr/](docs/adr/README.md) | Architecture Decision Records: the *why* behind key choices |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Trade-off table and measured performance |
| [docs/AI_USAGE.md](docs/AI_USAGE.md) | How AI was used to build this, and where it was wrong |
| [CLAUDE.md](CLAUDE.md) | Standing instructions given to the AI coding agent |
| [docs/DEMO.md](docs/DEMO.md) | Shot list for the video demo |
| [docs/ASSIGNMENT.md](docs/ASSIGNMENT.md) | Original brief |

## What the HR manager can do

- **Employee directory (home page):** search 10k employees by name/email; filter by country,
  department, job title, job level, currency and salary range (in the chosen currency, else
  USD); sort (salary sorts compare in USD terms); paginate.
- **Add / edit / remove employees,** with the same validation in the browser and on the server.
- **Salary history:** every salary or currency change is recorded with a reason, the date it
  takes effect (backdating allowed) and who made it.
- **Pay insights** (button on the home page → `/insights`): headline org numbers; per-country
  min/median/average/max (local currency and USD); pay by job title within a country; pay by
  department.
- **Ask Salary Data** (chat, bottom-right on every page): averages and medians, department and
  country comparisons, pay gaps between levels, outliers against peers, who earns above their
  department's average, salary bands, and changes over the last 12 months. The model only picks
  one of nine allow-listed analytics operations; **every number comes from a SQL aggregate**,
  shown with a chart, the table behind it and its scope (currency basis, FX date).
  Vague questions get a clarifying question; individual-level answers need permission, and
  pay for groups under 3 people is hidden from anyone without it
  ([ADR 0008](docs/adr/0008-natural-language-salary-intelligence.md)).
- **Choose the model:** Ollama (local, private) by default; Claude or OpenAI when their API key
  is set (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`), selectable in the chat.

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

**Docker (everything: app, PostgreSQL, Ollama):** `make docker-up` → http://localhost:8000.
The container runs migrations, seeds on first boot only, then serves the UI and the API.

**Deploy (Render):** Dashboard → *New* → *Blueprint* → pick this repo. [render.yaml](render.yaml)
provisions PostgreSQL 17 and a web service from the Dockerfile, and wires the database URL in.
The first boot migrates and seeds 10,000 employees. Ollama isn't hosted there: set
`ANTHROPIC_API_KEY` or `OPENAI_API_KEY` (and `SALARY_LLM_PROVIDER`) in the dashboard to enable
Ask Salary Data; without a key it reports itself unavailable while everything else works. A demo script is in
[docs/DEMO.md](docs/DEMO.md).

Run `make help` for all tasks. Configuration: `SALARY_*` env vars, see
[backend/.env.example](backend/.env.example).

## Quality

```bash
make check        # what CI runs: lint + types + all tests
```

| | Backend | Frontend |
|---|---|---|
| Tests | 261 in ~12 s (on PostgreSQL) | 53 in ~5 s |
| Static checks | ruff (lint + format) | ESLint, `tsc --strict` |

- **Real database, still fast:** tests run on PostgreSQL (a throwaway container), each test in a
  rolled-back transaction; seeded RNG, fake LLM, mocked HTTP.
- **Architecture tests** enforce module boundaries ([ADR 0001](docs/adr/0001-modular-monolith.md)).
- **Migration drift test:** models and Alembic migrations can't diverge.
- **Query-plan tests:** every read path must use an index, with no full scans or in-memory
  sorts ([ADR 0006](docs/adr/0006-indexing.md)).
- **Salary-intelligence benchmark:** 11 predefined business questions answered through the full
  pipeline and checked against values recomputed from the seed generator
  ([tests/benchmark](backend/tests/benchmark)); `make benchmark-llm [provider=...]` checks a real
  model picks the right operations (llama3.2: 11/11).
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
