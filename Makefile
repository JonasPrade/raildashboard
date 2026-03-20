# Schienendashboard – common development tasks
#
# Run `make help` to list all targets.

BACKEND_DIR  := apps/backend
FRONTEND_DIR := apps/frontend
VENV         := $(BACKEND_DIR)/.venv
PYTHON       := $(VENV)/bin/python
PIP          := $(VENV)/bin/pip
UVICORN      := .venv/bin/uvicorn
PYTEST       := .venv/bin/pytest
ALEMBIC      := .venv/bin/alembic

.PHONY: help install install-backend install-frontend \
        dev dev-backend dev-frontend \
        build build-frontend \
        test test-backend test-frontend \
        lint lint-frontend \
        migrate migrate-create \
        backup-db restore-db list-backups \
        list-users create-user change-password \
        gen-api \
        list-parse-results dump-parse-result \
        celery-worker \
        docker-dev-up docker-dev-down \
        docker-prod-build docker-prod-up docker-prod-down \
        docker-migrate docker-create-user docker-backup-db docker-worker-logs \
        clean clean-backend clean-frontend

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

help:
	@echo ""
	@echo "Schienendashboard – available make targets"
	@echo ""
	@echo "  Setup"
	@echo "    install            Install all dependencies (backend + frontend)"
	@echo "    install-backend    Create Python venv and install requirements"
	@echo "    install-frontend   Run npm install in apps/frontend"
	@echo ""
	@echo "  Development"
	@echo "    dev                Start backend and frontend concurrently"
	@echo "    dev-backend        Start uvicorn with --reload"
	@echo "    dev-frontend       Start Vite dev server"
	@echo ""
	@echo "  Build"
	@echo "    build              Build the frontend for production"
	@echo ""
	@echo "  Testing & quality"
	@echo "    test               Run all tests (backend + frontend)"
	@echo "    test-backend       Run pytest"
	@echo "    test-frontend      Run Vitest"
	@echo "    lint               Run all linters"
	@echo "    lint-frontend      Run ESLint on the frontend"
	@echo ""
	@echo "  Database"
	@echo "    migrate            Apply all pending Alembic migrations"
	@echo "    migrate-create     Create a new Alembic revision"
	@echo "                       Usage: make migrate-create MSG='your message'"
	@echo "    backup-db          Create a pg_dump of the configured database"
	@echo "                       Optional: DB_URL=postgresql://... or ENV_FILE=.env"
	@echo "    restore-db         Restore a dump into the configured database"
	@echo "                       Usage: make restore-db BACKUP=backups/file.dump"
	@echo "                       Optional: DB_URL=postgresql://... or ENV_FILE=.env"
	@echo "    list-backups       List all local dump files with size and date"
	@echo ""
	@echo "  User management"
	@echo "    list-users         List all users with their roles"
	@echo "    create-user        Create a new user"
	@echo "                       Usage: make create-user USERNAME=admin ROLE=admin"
	@echo "    change-password    Change password for an existing user"
	@echo "                       Usage: make change-password USERNAME=admin"
	@echo ""
	@echo "  Code generation"
	@echo "    gen-api            Regenerate frontend API client from OpenAPI schema"
	@echo "                       (requires backend running at http://localhost:8000)"
	@echo ""
	@echo "  Docker – development (DB + Redis only)"
	@echo "    docker-dev-up      Start the dev DB + Redis containers"
	@echo "    docker-dev-down    Stop the dev containers (data volume is preserved)"
	@echo ""
	@echo "  Celery"
	@echo "    celery-worker      Start Celery worker (requires Redis running)"
	@echo ""
	@echo "  Docker – production (full stack)"
	@echo "    docker-prod-build  Build all Docker images (requires .env)"
	@echo "    docker-prod-up     Start the production stack in the background"
	@echo "    docker-prod-down   Stop the production stack"
	@echo "    docker-migrate     Run Alembic migrations inside the backend container"
	@echo "    docker-create-user Create a user inside the backend container"
	@echo "                       Usage: make docker-create-user USERNAME=admin ROLE=admin"
	@echo "    docker-backup-db   pg_dump via docker exec on the db container"
	@echo "    docker-worker-logs Tail Celery worker logs in the prod stack"
	@echo ""
	@echo "  Cleanup"
	@echo "    clean              Remove all build artefacts and caches"
	@echo ""

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

install: install-backend install-frontend

install-backend:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt

install-frontend:
	npm --prefix $(FRONTEND_DIR) install

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------

# Start both services in the foreground using a simple parallel shell trick.
# Ctrl-C stops both processes.
dev:
	@trap 'kill 0' INT; \
	  $(MAKE) dev-backend & \
	  $(MAKE) dev-frontend & \
	  $(MAKE) celery-worker & \
	  wait

dev-backend:
	cd $(BACKEND_DIR) && $(UVICORN) main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	npm --prefix $(FRONTEND_DIR) run dev

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

build: build-frontend

build-frontend:
	npm --prefix $(FRONTEND_DIR) run build

# ---------------------------------------------------------------------------
# Testing & quality
# ---------------------------------------------------------------------------

test: test-backend test-frontend

test-backend:
	cd $(BACKEND_DIR) && ENVIRONMENT=test $(PYTEST)

test-frontend:
	npm --prefix $(FRONTEND_DIR) run test

lint: lint-frontend

lint-frontend:
	npm --prefix $(FRONTEND_DIR) run lint

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

migrate:
	cd $(BACKEND_DIR) && $(ALEMBIC) upgrade head

# Usage: make migrate-create MSG="add user table"
migrate-create:
	@if [ -z "$(MSG)" ]; then echo "Usage: make migrate-create MSG='your message'"; exit 1; fi
	cd $(BACKEND_DIR) && $(ALEMBIC) revision --autogenerate -m "$(MSG)"

# ---------------------------------------------------------------------------
# Backup & Restore
# ---------------------------------------------------------------------------

# Create a pg_dump of the configured database.
# Optional overrides: DB_URL="postgresql://..." or ENV_FILE=.env
backup-db:
	@DB_URL="$(DB_URL)" ENV_FILE="$(ENV_FILE)" bash scripts/backup_db.sh

# Restore a dump into the configured database.
# Usage: make restore-db BACKUP=backups/raildashboard_20260101_020000.dump
# Optional overrides: DB_URL="postgresql://..." or ENV_FILE=.env
restore-db:
	@if [ -z "$(BACKUP)" ]; then \
	    echo "Usage: make restore-db BACKUP=backups/<dateiname>.dump"; exit 1; \
	fi
	@DB_URL="$(DB_URL)" ENV_FILE="$(ENV_FILE)" bash scripts/restore_db.sh "$(BACKUP)"

# List all local dump files with size and date.
list-backups:
	@if [ ! -d backups ] || [ -z "$$(ls backups/raildashboard_*.dump 2>/dev/null)" ]; then \
	    echo "Keine Backup-Dateien in backups/ gefunden."; \
	else \
	    ls -lh backups/raildashboard_*.dump | awk '{print $$5, $$6, $$7, $$8, $$9}'; \
	fi

# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

list-users:
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/python scripts/list_users.py

# Usage: make create-user USERNAME=admin ROLE=admin
create-user:
	@if [ -z "$(USERNAME)" ]; then echo "Usage: make create-user USERNAME=<name> ROLE=<viewer|editor|admin>"; exit 1; fi
	@if [ -z "$(ROLE)" ]; then echo "Usage: make create-user USERNAME=<name> ROLE=<viewer|editor|admin>"; exit 1; fi
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/python scripts/create_initial_user.py --username $(USERNAME) --role $(ROLE)

# Usage: make change-password USERNAME=admin
change-password:
	@if [ -z "$(USERNAME)" ]; then echo "Usage: make change-password USERNAME=<name>"; exit 1; fi
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/python scripts/change_password.py --username $(USERNAME)

# Usage: make delete-user USERNAME=admin
delete-user:
	@if [ -z "$(USERNAME)" ]; then echo "Usage: make delete-user USERNAME=<name>"; exit 1; fi
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/python scripts/delete_user.py --username $(USERNAME)

# ---------------------------------------------------------------------------
# Code generation
# ---------------------------------------------------------------------------

gen-api:
	npm --prefix $(FRONTEND_DIR) run gen:api
	npm --prefix $(FRONTEND_DIR) run gen:zod

# ---------------------------------------------------------------------------
# Haushalt debugging
# ---------------------------------------------------------------------------

# List all parse results:        make list-parse-results
# Dump JSON for ID 3:            make dump-parse-result ID=3
# Write JSON to file:            make dump-parse-result ID=3 > /tmp/result.json
list-parse-results:
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/python scripts/dump_parse_result.py

dump-parse-result:
	@if [ -z "$(ID)" ]; then echo "Usage: make dump-parse-result ID=<id>"; exit 1; fi
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/python scripts/dump_parse_result.py $(ID)

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------

# Start a Celery worker locally (requires Redis running, e.g. via make docker-dev-up).
celery-worker:
	cd $(BACKEND_DIR) && PYTHONPATH=. .venv/bin/celery -A dashboard_backend.celery_app worker --loglevel=info

# ---------------------------------------------------------------------------
# Docker – development (DB + Redis)
# ---------------------------------------------------------------------------

docker-dev-up:
	docker compose -f docker-compose.dev.yml up -d

docker-dev-down:
	docker compose -f docker-compose.dev.yml down

# ---------------------------------------------------------------------------
# Docker – production (full stack)
# ---------------------------------------------------------------------------

docker-prod-build:
	docker compose --env-file .env build

docker-prod-up:
	docker compose --env-file .env up -d

docker-prod-down:
	docker compose --env-file .env down

# Run Alembic migrations inside the running backend container.
docker-migrate:
	docker compose exec backend alembic upgrade head

# Create a user inside the running backend container.
# Usage: make docker-create-user USERNAME=admin ROLE=admin
docker-create-user:
	@if [ -z "$(USERNAME)" ]; then echo "Usage: make docker-create-user USERNAME=<name> ROLE=<viewer|editor|admin>"; exit 1; fi
	@if [ -z "$(ROLE)" ]; then echo "Usage: make docker-create-user USERNAME=<name> ROLE=<viewer|editor|admin>"; exit 1; fi
	docker compose exec backend python scripts/create_initial_user.py --username $(USERNAME) --role $(ROLE)

# Usage: make docker-delete-user USERNAME=admin
docker-delete-user:
	@if [ -z "$(USERNAME)" ]; then echo "Usage: make docker-delete-user USERNAME=<name>"; exit 1; fi
	docker compose exec backend python scripts/delete_user.py --username $(USERNAME)

# Tail Celery worker logs in the prod stack.
docker-worker-logs:
	docker compose --env-file .env logs -f worker

# Create a pg_dump via docker exec on the db container.
# The dump is written to the local backups/ directory.
docker-backup-db:
	@mkdir -p backups
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	  FILE="backups/raildashboard_$${TIMESTAMP}.dump"; \
	  docker compose exec db pg_dump -U raildashboard -Fc raildashboard > "$$FILE" && \
	  echo "Backup written to $$FILE"

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

clean: clean-backend clean-frontend

clean-backend:
	rm -rf $(VENV)
	find $(BACKEND_DIR) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND_DIR) -name "*.pyc" -delete 2>/dev/null || true

clean-frontend:
	rm -rf $(FRONTEND_DIR)/node_modules
	rm -rf $(FRONTEND_DIR)/dist
