# Shantranj — dev workflow (docker-first; works in Git Bash / Linux / WSL)

COMPOSE_DEV  := docker compose -f devops/compose/docker-compose.dev.yml
COMPOSE_PROD := docker compose -f devops/compose/docker-compose.prod.yml

.PHONY: help env up down logs ps build migrate revision seed \
        test test-backend test-engine test-frontend \
        lint fmt typecheck prod-up prod-down

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

env: ## Create .env from .env.example if missing
	@test -f .env || cp .env.example .env

up: env ## Start the dev stack (build if needed)
	$(COMPOSE_DEV) up -d --build

down: ## Stop the dev stack
	$(COMPOSE_DEV) down

logs: ## Tail all service logs
	$(COMPOSE_DEV) logs -f --tail=100

ps: ## Show service status
	$(COMPOSE_DEV) ps

build: ## Rebuild all images
	$(COMPOSE_DEV) build

migrate: ## Apply DB migrations (Phase 1+)
	$(COMPOSE_DEV) run --rm backend alembic upgrade head

revision: ## Create a new Alembic revision: make revision m="message"
	$(COMPOSE_DEV) run --rm backend alembic revision --autogenerate -m "$(m)"

seed: ## Seed the database (Phase 2+)
	$(COMPOSE_DEV) run --rm backend python -m app.db.seed

test: test-backend test-engine test-frontend ## Run all test suites

e2e: ## Playwright happy-path smoke against the running stack (:8080)
	cd frontend && npx playwright test

loadtest: ## k6 load-sanity against the running stack (needs k6 installed)
	k6 run -e BASE=http://localhost:8080 devops/loadtest/browse.js

backup: ## Run a one-off prod DB backup
	sh devops/prod/backup.sh

test-backend: ## Backend pytest
	$(COMPOSE_DEV) run --rm backend pytest

test-engine: ## Engine pytest
	$(COMPOSE_DEV) run --rm engine pytest

test-frontend: ## Frontend vitest
	cd frontend && npm test

lint: ## Ruff + eslint
	$(COMPOSE_DEV) run --rm backend ruff check .
	$(COMPOSE_DEV) run --rm engine ruff check .
	cd frontend && npm run lint

fmt: ## Auto-format (ruff format)
	$(COMPOSE_DEV) run --rm backend ruff format .
	$(COMPOSE_DEV) run --rm engine ruff format .

typecheck: ## mypy strict
	$(COMPOSE_DEV) run --rm backend mypy app
	$(COMPOSE_DEV) run --rm engine mypy app

prod-up: ## Start prod stack (Phase 9)
	$(COMPOSE_PROD) up -d --build

prod-down: ## Stop prod stack
	$(COMPOSE_PROD) down
