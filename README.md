# Schienendashboard

A web application that aggregates nationwide railway infrastructure and project information. It consists of a **FastAPI backend** (Python) and a **React frontend** (TypeScript/Vite), both living in the `apps/` directory.

> **Language note:** Code, documentation, and commit messages are written in English. UI content is presented in German.

## Repository layout

```
├── apps/
│   ├── backend/   # FastAPI + SQLAlchemy + PostGIS
│   └── frontend/  # React + Vite + Mantine + MapLibre
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
| PostgreSQL + PostGIS | 15+ |

## Quick start

```bash
# Copy and fill in the environment file
cp .env.example apps/backend/.env

# Install all dependencies and start both services
make install
make dev
```

`make dev` starts the backend on `http://localhost:8000` and the frontend on `http://localhost:5173`.

See `Makefile` for the full list of available targets.

## Configuration

All runtime configuration is managed through a `.env` file in `apps/backend/`. A reference file with all supported variables lives at `.env.example` in the repository root.

| Variable | Used by | Description |
|---|---|---|
| `DATABASE_URL` | Backend | PostgreSQL connection string (PostGIS required) |
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
| `VITE_TILE_LAYER_URL` | Frontend | Raster tile layer URL for the map view |

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
cd apps/backend
alembic upgrade head
# Create a new migration after model changes:
alembic revision --autogenerate -m "Description"
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

## Contributing

Read `AGENT.md` before making changes. It covers architecture guidelines, Git workflow, code quality standards, and PR requirements for both apps.

## Licence

Internal project. A licence will be added before public release.
