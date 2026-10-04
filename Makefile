# DNNLS Live Arena - convenience targets (Windows: use scripts/arena.ps1 or the docker compose
# commands shown next to each target).
COMPOSE      = docker compose
COMPOSE_DEV  = docker compose -f docker-compose.yml -f docker-compose.dev.yml
NODE         = docker run --rm -it -v "$(CURDIR)/frontend":/fe -w /fe -u "$(shell id -u):$(shell id -g)" -e HOME=/tmp node:20-alpine

.PHONY: help up down logs restart build runner demo test test-local lint typecheck dev dev-down shell psql migrate migration clean

help:
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/' | column -t -s $$'\t'

up: ## Build and start everything (classroom mode)        -> docker compose up -d --build
	@test -f .env || cp .env.example .env
	$(COMPOSE) up -d --build

down: ## Stop everything (data is kept)                      -> docker compose down
	$(COMPOSE) down

logs: ## Follow logs                                         -> docker compose logs -f
	$(COMPOSE) logs -f

restart: ## Restart web + worker
	$(COMPOSE) restart web worker

build: ## Rebuild the app image                              -> docker compose build web
	$(COMPOSE) build web

runner: ## Rebuild the sandbox runner image                  -> docker compose build runner-builder
	$(COMPOSE) build runner-builder

demo: ## Seed the demo session (needs `make up`)             -> docker compose exec web python -m app.scripts.seed_demo
	$(COMPOSE) exec web python -m app.scripts.seed_demo

test: ## Run the full test suite inside the worker container (includes sandbox tests)
	$(COMPOSE) run --rm --no-deps -e DATA_DIR=/data/tests -e TEST_DATABASE_URL=sqlite:////tmp/test.db worker sh -c "pytest -q; rc=$$?; rm -rf /data/tests; exit $$rc"

test-local: ## Run tests with the local virtualenv (backend/.venv)
	cd backend && .venv/bin/python -m pytest -q

lint: ## Ruff (format check + lint)
	$(COMPOSE) run --rm --no-deps worker sh -c "ruff format --check . && ruff check ."

typecheck: ## TypeScript check of the frontend
	$(NODE) npx tsc --noEmit

dev: ## Live-reload development stack (API :8000, Vite :5173)
	@test -f .env || cp .env.example .env
	$(COMPOSE_DEV) up --build

dev-down:
	$(COMPOSE_DEV) down

shell: ## Shell in the web container
	$(COMPOSE) exec web bash

psql: ## psql into the database
	$(COMPOSE) exec db psql -U arena arena

migrate: ## Apply migrations
	$(COMPOSE) exec web alembic upgrade head

migration: ## Autogenerate a migration: make migration m="add foo"
	$(COMPOSE) exec web alembic revision --autogenerate -m "$(m)"

clean: ## Stop and DELETE all data volumes
	$(COMPOSE) down -v
