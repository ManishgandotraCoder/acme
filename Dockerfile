# --- 1. Build the React app -------------------------------------------------------------
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- 2. Python runtime serving API + built UI ---------------------------------------------
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.8.4 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/app ./app
COPY backend/alembic.ini ./
COPY backend/migrations ./migrations
COPY --from=web /web/dist ./static

# SALARY_DATABASE_URL (PostgreSQL) is supplied by the environment: docker compose or the host.
ENV SALARY_STATIC_DIR=/app/static \
    PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

# Migrate, seed 10k employees on first boot only, then serve.
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed.run --if-empty && uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
