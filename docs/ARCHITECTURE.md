# Architecture

## System overview

```mermaid
flowchart LR
    HR([HR Manager]) --> UI

    subgraph Browser
        UI[React + TypeScript<br/>Mantine · TanStack Query]
    end

    subgraph "FastAPI app (uvicorn)"
        API[Routers<br/>employees · insights · ask]
        ES[EmployeeService]
        IS[InsightsService]
        AS[AskService]
        REPO[EmployeeRepository]
        FX[(domain/countries<br/>currencies + FX)]
        API --> ES & IS & AS
        ES --> REPO
        AS --> IS
        AS -->|LLMClient port| OC[OllamaClient]
        ES & IS --> FX
    end

    UI -->|JSON /api| API
    REPO --> DB[(SQLite)]
    IS --> DB
    OC -->|/api/chat, JSON schema| OL[Ollama · llama3.2]
```

In production a single container serves both the API and the built React app (FastAPI
`StaticFiles` + SPA fallback), so there is one thing to deploy.

## Layers (backend)

| Layer | Responsibility | Knows about |
|---|---|---|
| `api/` | HTTP: parsing, status codes, DI of session + LLM, error → status mapping | services, schemas |
| `services/` | Use-cases and business rules; owns the transaction (`commit`) | repositories, domain |
| `repositories/` | Query construction (filters, search, paging, sort) | ORM models |
| `domain/` | Pure rules: supported countries, currency, FX conversion | nothing |
| `ai/` | `LLMClient` protocol, Ollama adapter, `AskService` | insights service |

Dependencies point inwards. Domain errors (`EmployeeNotFoundError`, `DuplicateEmailError`,
`CurrencyChangeRequiresSalaryError`, `UnsupportedCountryError`, `LLMUnavailableError`) are
plain Python exceptions mapped to HTTP in one place ([api/errors.py](../backend/app/api/errors.py)),
so services stay framework-free and unit-testable.

`create_app(settings, llm=...)` is a factory: tests inject an in-memory database and a stub
LLM; production wires the real Ollama client.

## Data model

```mermaid
erDiagram
    EMPLOYEE ||--o{ SALARY_CHANGE : "has history"
    EMPLOYEE {
        int id PK
        string full_name "indexed"
        string email "unique, lower-cased"
        string job_title "indexed"
        string department "indexed"
        string country "indexed"
        string currency "derived from country"
        int annual_salary "local currency, whole units, indexed"
        date hire_date
        datetime created_at
        datetime updated_at
    }
    SALARY_CHANGE {
        int id PK
        int employee_id FK "cascade delete"
        int previous_salary
        int new_salary
        string previous_currency
        string new_currency
        string reason
        datetime changed_at
    }
```

Composite index `(country, job_title)` serves the most common insight query.

## "Ask AI" flow — the model never produces numbers

```mermaid
sequenceDiagram
    participant UI
    participant API as POST /api/ask
    participant AS as AskService
    participant LLM as Ollama (llama3.2)
    participant IS as InsightsService
    UI->>API: "What do data analysts earn in Germany?"
    API->>AS: ask(question)
    AS->>LLM: system prompt (real countries/titles/departments) + JSON schema, temperature 0
    LLM-->>AS: {"metric": "job_title_stats", "job_title": "Data Analyst"}  (dropped "Germany")
    Note over AS: Verify: entities read from the question text,<br/>model values kept only if known AND grounded<br/>→ country = Germany recovered
    AS->>IS: job_title_stats("Germany")
    IS-->>AS: rows from SQL
    AS-->>UI: templated answer + interpreted intent + raw rows
```

The UI shows the interpreted intent as badges ("Country: Germany", "Job title: Data
Analyst"), so the HR manager can see what was answered.

## Frontend

- `api/` — a typed `request()` wrapper (JSON, query strings, FastAPI validation errors
  flattened to readable messages) plus one `api` object mirroring the endpoints.
- `features/<feature>/` — page, components, React Query hooks and their tests side by side.
- Server state lives in TanStack Query (caching, `keepPreviousData` for smooth paging,
  invalidation after writes); UI state stays local. No global store needed.
- Routes are lazy-loaded, so the charting library only downloads for *Pay insights*.
