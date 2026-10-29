# 0005 — Single container serving API and UI

**Status:** Accepted

## Context
An internal tool for one team. Separate frontend hosting adds CORS, two deploy pipelines
and version skew between UI and API.

## Decision
A multi-stage Dockerfile builds the React app and serves it from FastAPI (`core/frontend.py`,
SPA fallback, `/api/*` 404s preserved). Container start: migrate → seed if empty → serve.
The database is PostgreSQL ([ADR 0007](0007-postgresql.md)), supplied via
`SALARY_DATABASE_URL`; `docker-compose.yml` runs Postgres and Ollama alongside the app. Health: `/api/health` (liveness), `/api/ready` (DB).

## Consequences
- ✅ One artifact, one URL, UI and API always in step.
- ❌ UI and API scale together; put static assets behind a CDN if traffic ever demands it.
