# ACME Salary Management

Web application for ACME's HR Manager to manage salary data for 10,000 employees across
10 countries and answer "how do we pay people?" questions — replacing spreadsheets.

**Stack:** Python 3.12 · FastAPI on uvicorn · SQLAlchemy 2 + SQLite · React 19 + TypeScript ·
Mantine · TanStack Query · Ollama (local LLM) · pytest · Vitest + Testing Library · Docker

| | |
|---|---|
| 📄 Requirements (written first) | [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) |
| 🏗️ Architecture & diagrams | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| ⚖️ Decisions, trade-offs, performance | [docs/DECISIONS.md](docs/DECISIONS.md) |
| 🤖 How AI was used (and where it was wrong) | [docs/AI_USAGE.md](docs/AI_USAGE.md) |
| 📋 Original brief | [docs/ASSIGNMENT.md](docs/ASSIGNMENT.md) |

## What the HR manager can do

- **Employee directory** — search 10k employees by name/email, filter by country, department
  and job title, sort (salary sorts compare in USD terms), paginate.
- **Add / edit / remove employees** with validation mirrored client- and server-side.
- **Salary history** — every salary or currency change is recorded with a reason.
- **Pay insights** — org headline numbers, per-country min/median/average/max (local currency
  and USD), pay by job title within a country, pay by department.
- **Ask AI** — "What do data analysts earn in Germany?" A local Ollama model interprets the
  question; **every number comes from the database**, never from the model.

## Run it

### Option A — Docker (one command)
```bash
docker compose up --build          # http://localhost:8000 (UI + API + Ollama)
```
The database seeds 10,000 employees on first boot. The Ollama container pulls `llama3.2` on
start; until it's ready, *Ask AI* shows a friendly "unavailable" message and everything else works.

### Option B — local development
Prerequisites: Python 3.12 + [uv](https://docs.astral.sh/uv/), Node 22, optionally
[Ollama](https://ollama.com) with `ollama pull llama3.2`.

```bash
# Backend — http://localhost:8000/docs
cd backend
uv sync
uv run python -m app.seed.run --count 10000 --reset
uv run uvicorn app.main:create_app --factory --reload

# Frontend — http://localhost:5173 (proxies /api to :8000)
cd frontend
npm install
npm run dev
```

Configuration (env vars, prefix `SALARY_`): `DATABASE_URL`, `OLLAMA_URL`, `OLLAMA_MODEL`,
`OLLAMA_TIMEOUT_SECONDS`, `CORS_ORIGINS`, `STATIC_DIR` — see [backend/app/config.py](backend/app/config.py).

## Tests

```bash
cd backend && uv run pytest --cov=app     # 86 tests, ~0.5s, 97% coverage
cd frontend && npm test                    # 26 tests, ~3s
```
Tests are deterministic: in-memory SQLite per test, seeded RNG, a fake LLM (no network),
`httpx.MockTransport` for the Ollama adapter, and mocked API calls in UI tests. Warnings fail
the backend suite. CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs lint, tests,
build and the Docker image on every PR.

## Repository layout

```
backend/
  app/
    domain/countries.py      countries, currencies, static FX table
    models.py                Employee, SalaryChange (SQLAlchemy)
    repositories/            query building: search, filters, paging, sort
    services/                use-cases: EmployeeService, InsightsService
    ai/                      LLM port, Ollama adapter, AskService
    api/                     FastAPI routers, DI, error mapping
    seed/                    deterministic generator + first/last name files
  tests/unit, tests/api
frontend/src/
  api/                       typed client mirroring backend schemas
  features/{employees,insights,ask}/   pages, components, hooks (+ tests alongside)
docs/                        requirements, architecture, decisions, AI usage
```

## Commit history
The history is intentionally incremental and test-first: each feature lands as tests + the
implementation that makes them pass, and two `fix:` commits capture bugs found by running
the real system (LLM entity hallucination, cross-currency sorting) together with the
regression tests that pin them. `git log --oneline --reverse` reads as the build story.
