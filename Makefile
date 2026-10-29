# One entry point for common tasks. Run `make help`.
.DEFAULT_GOAL := help
SHELL := /bin/bash -o pipefail
BACKEND := cd backend &&
FRONTEND := cd frontend &&

.PHONY: help setup dev-api dev-web test test-api test-web lint format check \
        db-migrate db-seed db-reset migration docker-up docker-down

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Install backend + frontend dependencies and git hooks
	$(BACKEND) uv sync
	$(FRONTEND) npm ci
	uvx pre-commit install

dev-api: ## Run the API with reload on :8000
	$(BACKEND) uv run uvicorn app.main:create_app --factory --reload

dev-web: ## Run the UI on :5173 (proxies /api to :8000)
	$(FRONTEND) npm run dev

test: test-api test-web ## Run all tests

test-api: ## Backend tests with coverage
	$(BACKEND) uv run pytest --cov=app --cov-report=term-missing:skip-covered

test-web: ## Frontend tests
	$(FRONTEND) npm test

lint: ## Lint + type-check everything
	$(BACKEND) uv run ruff check . && uv run ruff format --check .
	$(FRONTEND) npm run lint && npx tsc -b

format: ## Auto-format backend code
	$(BACKEND) uv run ruff check --fix . && uv run ruff format .

check: lint test ## What CI runs

db-migrate: ## Apply database migrations
	$(BACKEND) uv run alembic upgrade head

db-seed: ## Seed 10,000 employees (replacing existing ones)
	$(BACKEND) uv run python -m app.seed.run --count 10000 --reset

db-reset: ## Delete the local database, migrate and seed
	rm -f backend/salary.db backend/salary.db-wal backend/salary.db-shm
	$(MAKE) db-migrate db-seed

migration: ## Create a migration from model changes: make migration m="add bonus column"
	$(BACKEND) uv run alembic revision --autogenerate -m "$(m)"

docker-up: ## Build and run app + Ollama with Docker Compose
	docker compose up --build

docker-down: ## Stop Docker Compose services
	docker compose down
