# Schienendashboard Backend

The Schienendashboard project aggregates nationwide railway infrastructure and project information. This repository contains the FastAPI backend together with the database schema and import utilities that ingest project and infrastructure data from sources such as ERA RINF.

## Key Features
- **FastAPI REST API:** Exposes endpoints for projects, infrastructure objects, and routing information under `/api/v1`.
- **Routing microservice integration:** Computes rail routes via a dedicated microservice, caches the geometry in PostGIS, and
  exposes CRUD-style APIs for reuse.
- **PostgreSQL/PostGIS storage:** Persists geometries and metadata for railway infrastructure in a spatial database.
- **Import and ETL tooling:** Scripts under `scripts/` assist with loading external datasets, e.g. ERA RINF XML or legacy databases.
- **Modular architecture:** Clear separation of API, database models, CRUD layer, and schemas simplifies maintenance and feature work.

## Project Structure
```
.
├── main.py                     # FastAPI application and router registration
├── dashboard_backend/
│   ├── api/                    # Routers, endpoints, and response models
│   ├── core/                   # Configuration (environment variables, settings)
│   ├── crud/                   # Database access layer
│   ├── models/                 # SQLAlchemy models
│   ├── routing/                # Routing-related services
│   └── schemas/                # Pydantic schemas for requests/responses
├── scripts/                    # Data imports and generators
├── alembic/                    # Database migrations
├── docs/                       # Project and domain documentation
└── tests/                      # Pytest suites
```
See `docs/architecture.md` (repo root) for architectural background and `docs/roadmap.md` (repo root) for the project roadmap. Backend-specific implementation details remain in `docs/` (this directory).

## Prerequisites
- Python 3.11 (or newer)
- PostgreSQL with the PostGIS extension
- `.env` file in the repository root (copy from `.env.example` in repo root)

## Installation
1. Clone the repository and change into the project directory.
2. Create and activate a virtual environment (`python -m venv .venv && source .venv/bin/activate`).
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration
Application settings are read via Pydantic Settings from a `.env` file in the **repository root** (not in this directory). Important variables include:

| Variable        | Description                                                      |
|-----------------|------------------------------------------------------------------|
| `DATABASE_URL`  | PostgreSQL connection string pointing to the PostGIS database    |
| `RINF_API_URL`  | Base URL of the ERA RINF API                                     |
| `RINF_USERNAME` | Username for ERA RINF                                            |
| `RINF_PASSWORD` | Password for ERA RINF                                            |
| `ROUTING_BASE_URL` | Base URL of the routing microservice (e.g. GraphHopper)          |
| `ROUTING_TIMEOUT_SECONDS` | Optional: request timeout for the routing client (default `20`) |
| `GRAPH_VERSION` | Identifier for the routing graph build used for caching           |
| `ENVIRONMENT`   | Optional: selects alternative `.env` files (e.g. `.env.test`)    |
| `OSM_PBF_DIR`   | Optional: directory containing `<COUNTRY>.osm.pbf` extracts for offline OSM imports |
| `USE_GEOMETRY`  | Optional: set to `0` to skip geometry creation during OSM offline imports |

## Database Migrations
Alembic revisions live in `alembic/versions`. Apply schema changes with:
```bash
alembic upgrade head
```
During development, create new revisions via `alembic revision --autogenerate -m "Description"`.

## Running the Application
After configuring the environment, start the development server with:
```bash
uvicorn main:app --reload
```
Interactive API documentation is available at `http://localhost:8000/docs`.

## Routing API
The backend persists rail routes that are computed via the routing microservice. The following REST endpoints are available:

- `POST /api/v1/projects/{project_id}/routes`: triggers the routing microservice, stores the result in PostGIS, and returns the
  persisted route. Identical waypoint/profile/option combinations reuse the cached record.
- `GET /api/v1/projects/{project_id}/routes`: lists previously computed routes for a project with optional pagination
  parameters `limit` and `offset`.
- `GET /api/v1/routes/{route_id}`: retrieves the details of a stored route, including bounding box and GeoJSON geometry.

Routes are hashed with the routing graph version to keep the cache consistent with the deployed microservice.

## Testing
Pytest drives automated tests:
```bash
pytest
```
For database-dependent tests use a dedicated test database and set `ENVIRONMENT=test` so that `.env.test` is picked up.

## Data Imports
The `scripts/` directory contains helpers for ingesting external data sources:
- `import_rinf_data/import_xml.py`: Parses ERA RINF XML files and loads them into the database.
- `import_old_db/`: Utilities for migrating legacy datasets.
- `generate_rinf_models/`: Generators for models and schemas derived from RINF structures.
- `import_osm_railways.py`: Imports OpenStreetMap railway data either offline from `.osm.pbf` extracts or via the Overpass API.

### Offline OpenStreetMap workflow
Offline imports rely on the PostGIS-enabled database so that geometries can be stored and spatial indexes remain valid. Prepare the Geofabrik extracts and import them as follows:

1. Download the `.osm.pbf` extract for the target country from [Geofabrik](https://www.geofabrik.de/data/download.html) and place it inside `data/osm/` (or any custom directory referenced by `OSM_PBF_DIR`). Example for Germany:
   ```bash
   mkdir -p data/osm
   wget https://download.geofabrik.de/europe/germany-latest.osm.pbf -O data/osm/DE.osm.pbf
   ```
2. Install the optional high-performance parser dependency that accelerates `pyosmium` (already compatible with Python 3.11+):
   Not needed each time, just if not installed
   ```bash
   pip install python-rapidjson
   ```
   This step is optional but recommended for large extracts.
3. Ensure the PostGIS database is available (the script connects via `DATABASE_URL`) and run the importer from the repository root:
   Not needed each time, just if not installed
   ```bash
   # Uses data/osm/DE.osm.pbf automatically
   python scripts/import_osm_railways.py DE --cleanup-existing
   ```
4. When maintaining multiple country extracts, repeat the download/import cycle per ISO 3166-1 alpha-2 country code (e.g. `AT`, `CH`).

Additional flags:
- `--track-types`: restrict the railway types to import (default: `rail`, `light_rail`, `subway`, `tram`).
- `--use-overpass`: fall back to the legacy Overpass import if an offline extract is unavailable.
- `--cleanup-existing`: remove prior OSM entries for the country before importing (useful for full refreshes).

The script looks up PBF files in `OSM_PBF_DIR` (default: `data/osm`) when `--pbf-path` is omitted. Override the environment variable to point at a shared network drive or cache directory as needed.

Run other scripts from within the virtual environment, for example:
```bash
python scripts/import_rinf_data/import_xml.py --help
```

## Contributing

Consult **`AGENT.md`** at the repository root before making substantial changes. Backend-specific reminders are in `agent.md` (this directory).

- Follow the existing module layout (`api`, `crud`, `models`, `schemas`).
- Introduce new groups of database tables in dedicated subdirectories (e.g. `osmr`, `eba_data`, `project_data`).
- Add meaningful tests for new functionality.
- Update this README and relevant files in `docs/` whenever setup steps or data flows change.

## Further Documentation
Project-wide documentation (architecture, data models, roadmap) lives in `docs/` at the repository root.
This directory's `docs/` folder contains backend-specific implementation details (RINF import, data mapping, routing, user management). Review the relevant documents whenever introducing new features or import paths.

