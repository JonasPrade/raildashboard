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
        list-users create-user change-password \
        gen-api \
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

# ---------------------------------------------------------------------------
# Code generation
# ---------------------------------------------------------------------------

gen-api:
	npm --prefix $(FRONTEND_DIR) run gen:api
	npm --prefix $(FRONTEND_DIR) run gen:zod

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
