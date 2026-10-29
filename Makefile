# One entry point for common tasks. Run `make help`.
.DEFAULT_GOAL := help
SHELL := /bin/bash -o pipefail
BACKEND := cd backend &&
FRONTEND := cd frontend &&

.PHONY: help setup dev-api dev-web test test-api test-web lint format check \
        db-up db-down db-migrate db-seed db-reset db-shell migration docker-up docker-down \
        benchmark-llm

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Install backend + frontend dependencies and git hooks
	$(BACKEND) uv sync
	$(FRONTEND) npm ci
	uvx pre-commit install

dev-api: db-up ## Run the API with reload on :8000 (starts Postgres if needed)
	$(BACKEND) uv run uvicorn app.main:create_app --factory --reload

dev-web: ## Run the UI on :5173 (proxies /api to :8000)
	$(FRONTEND) npm run dev

test: test-api test-web ## Run all tests

test-api: ## Backend tests with coverage (needs Docker: starts a throwaway Postgres)
	$(BACKEND) uv run pytest --cov=app --cov-report=term-missing:skip-covered

test-web: ## Frontend tests
	$(FRONTEND) npm test

lint: ## Lint + type-check everything
	$(BACKEND) uv run ruff check . && uv run ruff format --check .
	$(FRONTEND) npm run lint && npx tsc -b

format: ## Auto-format backend code
	$(BACKEND) uv run ruff check --fix . && uv run ruff format .

check: lint test ## What CI runs

benchmark-llm: ## Ask the predefined questions to a real model (needs `make dev-api`): provider=anthropic
	$(BACKEND) uv run python -m tests.benchmark.live $(if $(provider),--provider $(provider))

db-up: ## Start local Postgres (docker compose, port 5433)
	docker compose up -d --wait postgres

db-down: ## Stop local Postgres (data is kept in a volume)
	docker compose stop postgres

db-shell: ## Open psql on the local database
	docker compose exec postgres psql -U salary -d salary

db-migrate: db-up ## Apply database migrations
	$(BACKEND) uv run alembic upgrade head

db-seed: ## Seed 10,000 employees (replacing existing ones)
	$(BACKEND) uv run python -m app.seed.run --count 10000 --reset

db-reset: db-up ## Drop all tables, migrate from scratch and seed
	$(BACKEND) uv run alembic downgrade base
	$(MAKE) db-migrate db-seed

migration: ## Create a migration from model changes: make migration m="add bonus column"
	$(BACKEND) uv run alembic revision --autogenerate -m "$(m)"

docker-up: ## Build and run app + Postgres + Ollama with Docker Compose
	docker compose --profile app up --build

docker-down: ## Stop Docker Compose services
	docker compose --profile app down
