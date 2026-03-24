# Schienendashboard

A web application that aggregates nationwide railway infrastructure and project information. It consists of a **FastAPI backend** (Python) and a **React frontend** (TypeScript/Vite), both living in the `apps/` directory.

> **Language note:** Code, documentation, and commit messages are written in English. UI content is presented in German.

## Repository layout

```
├── apps/
│   ├── backend/   # FastAPI + SQLAlchemy + PostGIS
│   └── frontend/  # React + Vite + Mantine + MapLibre
├── docs/          # Project-wide documentation (architecture, models, roadmap)
├── AGENT.md       # Contributor guidelines (read before making changes)
├── Makefile       # Common development commands
├── .env.example   # Environment variable reference
└── README.md      # This document
```

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| Node.js | 20+ |
| Docker + Docker Compose | (for database) |

## Quick start

The recommended setup runs **PostgreSQL in Docker** and the backend/frontend locally.

```bash
# 1. Copy and fill in environment files
cp .env.example .env
cp .env.docker-dev.example .env.docker-dev   # adjust DB credentials if needed

# 2. Start the PostgreSQL container (port 5433)
make docker-dev-up

# 3. Install dependencies
make install

# 4. Run database migrations
make migrate

# 5. Start backend, frontend, and Celery worker
make dev
```

`make dev` starts:
- Backend API on `http://localhost:8000` (interactive docs: `/docs`)
- Frontend on `http://localhost:5173`
- Celery worker for background tasks (PDF parsing)

Stop the database container when done:
```bash
make docker-dev-down   # data volume is preserved
```

See `Makefile` for the full list of available targets.

> **Local PostgreSQL:** If you already have PostgreSQL 15+ with PostGIS running locally, skip steps 1–2 and set `DATABASE_URL` in `.env` directly.

## Configuration

All runtime configuration is managed through a single `.env` file in the repository root. A reference file with all supported variables lives at `.env.example`.

| Variable | Used by | Description |
|---|---|---|
| `DATABASE_URL` | Backend | PostgreSQL connection string (PostGIS required) |
| `SESSION_SECRET_KEY` | Backend | Required. HMAC signing key for session cookies. Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `RINF_API_URL` | Backend | ERA RINF API base URL |
| `RINF_USERNAME` | Backend | ERA RINF username |
| `RINF_PASSWORD` | Backend | ERA RINF password |
| `ROUTING_BASE_URL` | Backend | Routing microservice base URL |
| `ROUTING_TIMEOUT_SECONDS` | Backend | Request timeout for routing client (default: `20`) |
| `GRAPH_VERSION` | Backend | Routing graph build identifier |
| `ENVIRONMENT` | Backend | Selects an alternative `.env` file (e.g. `.env.test`) |
| `OSM_PBF_DIR` | Backend | Directory for `.osm.pbf` extracts (default: `data/osm`) |
| `USE_GEOMETRY` | Backend | Set to `0` to skip geometry creation on OSM import |
| `VITE_API_BASE_URL` | Frontend | Backend API base URL (default: `http://localhost:8000`) |
| `REACT_APP_TILE_LAYER_URL` | Frontend | Raster tile layer URL for the map view |

## Backend

The backend is a FastAPI application backed by a PostgreSQL/PostGIS database. It exposes a REST API under `/api/v1` and integrates with an external routing microservice to compute and cache rail routes.

```bash
cd apps/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload
```

Interactive API docs: `http://localhost:8000/docs`

See `apps/backend/README.md` for the full backend reference (project structure, routing API, data imports, testing).

## Frontend

The frontend is a React/Vite application that visualises rail infrastructure projects on a map and provides a project management interface.

```bash
cd apps/frontend
npm install
npm run dev
```

The dev server runs on `http://localhost:5173`. The app expects the backend at `http://localhost:8000` (override with `VITE_API_BASE_URL`).

See `apps/frontend/README.md` for the full frontend reference (project structure, API code generation, quality checks).

## Database migrations

```bash
make migrate
# Create a new migration after model changes:
make migrate-create MSG="Description"
```

## API code generation

When the backend OpenAPI schema changes, regenerate the frontend client:

```bash
make gen-api
```

This requires the backend to be running at `http://localhost:8000`.

## Testing

```bash
# Backend
make test-backend

# Frontend
make test-frontend
```

## Data imports

Scripts for importing external data sources live in `apps/backend/scripts/`. See `apps/backend/README.md` for details on ERA RINF XML, OpenStreetMap, and legacy database imports.

## Docker

The full stack (database, backend, frontend) can be run in Docker. There is also a lightweight dev mode that runs only the database in Docker while the backend and frontend run locally.

**Development — DB in Docker, app locally:**

```bash
make docker-dev-up        # start PostgreSQL on port 5433
# update DATABASE_URL in .env (see .env.docker-dev.example)
make dev                  # run backend + frontend as usual
make docker-dev-down      # stop DB (data volume is preserved)
```

**Production — full stack in Docker (server needs only `docker-compose.yml` + `.env`):**

```bash
cp .env.example .env   # fill in passwords, domain, and APP_VERSION tag
make docker-prod-build             # Docker clones code from GitHub at APP_VERSION tag
make docker-prod-up                # start stack (port 80)
make docker-create-user USERNAME=admin ROLE=admin
make docker-prod-down              # stop stack
```

See [`docs/production_setup.md`](docs/production_setup.md) for the full deployment guide including data migration and backup procedures.

## Deployment

For production setup (server configuration, Docker deployment, automated backups, update procedures), see [`docs/production_setup.md`](docs/production_setup.md).

## Contributing

Read `AGENT.md` before making changes. It covers architecture guidelines, Git workflow, code quality standards, and PR requirements for both apps.

## Licence

Internal project. A licence will be added before public release.
