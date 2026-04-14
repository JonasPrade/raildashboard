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
- `libmagic` system library — required by `python-magic` for MIME byte-sniffing on file uploads:
  - **Debian/Ubuntu:** `sudo apt-get install libmagic1`
  - **macOS:** `brew install libmagic`
  - **Docker:** installed automatically via the `Dockerfile`

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
| `SESSION_SECRET_KEY` | Required. HMAC signing key for httpOnly session cookies. Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `RINF_API_URL`  | Optional: Base URL of the ERA RINF API                           |
| `RINF_USERNAME` | Optional: Username for ERA RINF                                  |
| `RINF_PASSWORD` | Optional: Password for ERA RINF                                  |
| `ROUTING_BASE_URL` | Base URL of the routing microservice (e.g. GraphHopper)          |
| `ROUTING_TIMEOUT_SECONDS` | Optional: request timeout for the routing client (default `20`) |
| `GRAPH_VERSION` | Identifier for the routing graph build used for caching           |
| `ENVIRONMENT`   | Optional: selects alternative `.env` files (e.g. `.env.test`)    |
| `OSM_PBF_DIR`   | Optional: directory containing `<COUNTRY>.osm.pbf` extracts for offline OSM imports |
| `USE_GEOMETRY`  | Optional: set to `0` to skip geometry creation during OSM offline imports |
| `CELERY_BROKER_URL` | Redis broker URL. Dev default (docker-compose.dev.yml): `redis://:devpassword@localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | Redis result backend URL. Dev default: `redis://:devpassword@localhost:6379/0` |

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

## Docker

The backend ships with a multi-stage `Dockerfile` (`apps/backend/Dockerfile`):

- **Builder stage** — installs Python dependencies into `/venv` using `python:3.12-slim`.
- **Runtime stage** — copies only the venv and application source; runs as a non-root user.

On container start, `docker-entrypoint.sh` waits for the database to be ready, runs `alembic upgrade head`, then launches uvicorn. All environment variables are passed via `docker-compose.yml` / `.env` — no `.env` file is baked into the image.

Use `make docker-prod-up` / `make docker-prod-down` from the repository root to manage the production stack. See [`docs/production_setup.md`](../../docs/production_setup.md) for the full deployment guide.

## Authentication API

Session-based login using a signed `httpOnly` cookie (no credentials stored on the client).

| Endpoint | Auth required | Description |
|---|---|---|
| `POST /api/v1/auth/session` | No | Validate `{ username, password }`, set signed `session` cookie (7-day expiry) |
| `DELETE /api/v1/auth/session` | Session cookie | Clear the session cookie (logout) |
| `GET /api/v1/users/me` | Session cookie or Basic Auth | Return the current user; used for session restore on page load |

The cookie is `httpOnly` (JS-inaccessible), `SameSite=Strict` (CSRF-safe), and `Secure` when `ENVIRONMENT=production`. Token signing uses HMAC-SHA256 with `SESSION_SECRET_KEY`. Implementation lives in `core/security.py` (`create_session_token`, `verify_session_token`, `require_session`, `require_auth`) and `api/v1/endpoints/auth.py`.

## Celery Worker

Long-running tasks (PDF parsing, route computation) run asynchronously via Celery with Redis as broker and result backend.

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `CELERY_BROKER_URL` | `redis://:devpassword@localhost:6379/0` | Redis broker URL (dev Docker Redis requires password) |
| `CELERY_RESULT_BACKEND` | `redis://:devpassword@localhost:6379/0` | Redis result backend URL |

### Dev — start worker locally

Redis must be running first (included in the dev Docker stack):

```bash
make docker-dev-up   # starts DB + Redis
make celery-worker   # starts worker in the foreground
```

### Prod — worker container

The production `docker-compose.yml` includes a dedicated `worker` service that uses the same backend image with the Celery command as entrypoint. It starts automatically with `make docker-prod-up`.

View worker logs:
```bash
make docker-worker-logs
```

### Task status polling

After starting a task the API returns a `task_id`. The frontend polls:

```
GET /api/v1/tasks/{task_id}
```

Response: `{ task_id, status, result, error }` — `status` is one of `PENDING`, `STARTED`, `SUCCESS`, `FAILURE`.
Both endpoints require a logged-in user.

### Tests

Tests use `CELERY_BROKER_URL=memory://` and `CELERY_RESULT_BACKEND=cache+memory://` (set in `tests/conftest.py`) combined with `task_always_eager=True` — tasks run synchronously in-process; no Redis instance required.

## Haushaltsberichte Import

Yearly import of Annex VWIB Part B (federal budget) as PDF. Requires `pdfplumber` (already in `requirements.txt`).

### Import workflow

1. **Upload PDF** — `POST /api/v1/import/haushalt/parse` (multipart: `pdf`, `year`) → returns `task_id`
2. **Poll task** — `GET /api/v1/tasks/{task_id}` until `status == "SUCCESS"`; result contains `parse_result_id`
3. **Review** — `GET /api/v1/import/haushalt/parse-result/{id}` returns full parse result (rows classified as `new` / `update` / `unmatched`). Each row includes pre-populated `project_ids` from existing `FinveToProject` associations.
4. **Confirm** — `POST /api/v1/import/haushalt/confirm` — transactionally writes Finve, Budget, BudgetTitelEntry; syncs `FinveToProject` for both `new` and `update` rows (bidirectional add/remove); 409 Conflict on double-import
5. **Unmatched rows** — `GET /api/v1/import/haushalt/unmatched?resolved=false`; resolve with `PATCH /api/v1/import/haushalt/unmatched/{id}`. Rows without a FinVe number (e.g. early-planning projects like `B0134 L 06`) are automatically placed here.

### PDF format notes (2026+)

The 2026 PDF has a different pdfplumber layout vs. prior years:
- First three columns (Lfd.Nr., FinVe, Bedarfsplan) are merged into one cell, e.g. `B0080 275 N19` — parsed by `_parse_combined_id_cell()`
- Kap./Titel sub-entries and nachrichtlich entries are embedded as multi-line cells in the main row — extracted by `_extract_inline_titel_entries()` / `_extract_nachrichtlich_entries()`
- Some entries carry a `(alt)` suffix on the Kapitel number (e.g. `Kap. 1202 (alt)`) — handled by the extended `_KAP_TITEL_RE` regex
- Projects in early planning phase have no FinVe number (`B0134 L 06`) — automatically classified as unmatched

All import endpoints require role `editor` or `admin`.

### Auto-suggestion matching

During parsing, new FinVes (not yet in DB) are automatically matched against all projects using fuzzy name similarity (`tasks/finve_matching.py`):
- Normalises both names (lowercase, strip ABS/NBS prefixes, punctuation → spaces)
- Scores with `difflib.SequenceMatcher` (60%) + token overlap (40%), threshold 0.45
- Top 3 matches stored as `suggested_project_ids`; pre-populated into `project_ids` for the review UI

### FinVe data in project detail

```
GET /api/v1/projects/{project_id}/finves
```

Returns all FinVes linked to a project with their full budget history including per-Haushaltstiteln breakdown (`BudgetTitelEntry`). Uses eager-loading (`joinedload`) for `budgets → titel_entries → titel`. No authentication required beyond the standard project read access.

### FinVe overview endpoint

```
GET /api/v1/finves/
```

Returns all FinVes with full budget history and linked projects. Requires any authenticated role (viewer/editor/admin). Response includes: `id`, `name`, `starting_year`, `cost_estimate_original`, `is_sammel_finve`, `temporary_finve_number`, `project_count`, `project_names`, `projects` (list of `{id, name}`), `budgets` (full `BudgetSummarySchema` with `titel_entries`). Implemented in `crud/finves.py`.

### SV-FinVe year-scoped project tracking

`finve_to_project` now has a `haushalt_year` column (migration `20260310001`):

| Value | Meaning |
|---|---|
| `NULL` | Permanent link — used for regular FinVes |
| `<year>` | Year-scoped link — used for Sammelfinanzierungsvereinbarungen |

Two partial unique indexes enforce uniqueness separately for permanent and year-scoped rows. During `POST /confirm`, SV-FinVes only sync the current import year's rows (preserving historical membership); regular FinVes sync the `NULL`-year rows as before. Deleting a confirmed parse result also removes its year-scoped `FinveToProject` rows.

### New models (migration `20260306001`)

| Table | Description |
|---|---|
| `haushalt_titel` | Lookup table for Haushaltskapitel/Titel |
| `budget_titel_entry` | Per-titel breakdown per Budget row |
| `haushalts_parse_result` | Persisted raw PDF parser output |
| `finve_change_log` / `finve_change_log_entry` | Finve change history |
| `budget_change_log` / `budget_change_log_entry` | Budget change history |
| `unmatched_budget_row` | Unresolved PDF rows |

### Project group membership

`ProjectSchema` now includes a `project_groups` list of lightweight refs (`ProjectGroupRef`: id, name, short_name, color). Editors and admins can update a project's group membership via the standard PATCH endpoint:

```
PATCH /api/v1/projects/{project_id}
Body: { "project_group_ids": [1, 3] }
```

When `project_group_ids` is present in the payload, `update_project()` (CRUD layer) replaces the many-to-many `project_to_project_group` rows atomically. Omitting the field leaves existing group assignments unchanged. Requires `editor` or `admin` role.

### BVWP assessment data

```
GET /api/v1/projects/{project_id}/bvwp
```

Returns the full BVWP assessment record for a project (`BvwpProjectDataSchema`, ~200 optional fields). Returns `404` if no BVWP data exists for that project — the frontend uses this to conditionally show the section. No authentication required. Implemented in `crud/projects/bvwp.py` + `schemas/projects/bvwp_schema.py`.

## Verkehrsinvestitionsbericht (VIB) Import

Yearly import of the Bundestag printed paper „Verkehrsinvestitionsbericht für das Berichtsjahr XXXX". Only **Section B** (Schienenwege der Eisenbahnen des Bundes) is imported; sections C and D are ignored.

### Import workflow

1. **Upload PDF** — `POST /api/v1/import/vib/parse` (multipart: `pdf`, `year`) → returns `task_id`
2. **Poll task** — `GET /api/v1/tasks/{task_id}` until `status == "SUCCESS"`
3. **Review** — `GET /api/v1/import/vib/parse-result/{task_id}` — returns all extracted `VibEntryProposed` objects with auto-matched `project_id` and `suggested_project_ids`
4. **Confirm** — `POST /api/v1/import/vib/confirm` — writes `VibReport` + `VibEntry` + `VibPfaEntry` rows; returns `{ report_id, entries_created, pfa_entries_created }`
5. **Project detail** — `GET /api/v1/projects/{id}/vib` — all VIB entries linked to a project, newest year first

All VIB import endpoints require role `editor` or `admin`.

### Extracted fields per entry

| Field | Source |
|---|---|
| `vib_section` | Heading regex (`B.4.x.x`) |
| `vib_name_raw` | TOC lookup (canonical name) |
| `category` | Section number: B.4.1=laufend, B.4.2=neu, B.4.3=potentiell |
| `planungsstand` | Label `Planungsstand:` in body text |
| `bauaktivitaeten` | Label `Bauaktivitäten [year]:` |
| `teilinbetriebnahmen` | Label `Teilinbetriebnahmen [year]:` |
| `verkehrliche_zielsetzung` | Label `Verkehrliche Zielsetzung` |
| `strecklaenge_km`, `gesamtkosten_mio_eur`, `entwurfsgeschwindigkeit` | Regex on `Projektkenndaten` block |
| `raw_text` | Full accumulated plain text (capped at 8 000 chars) |
| `pfa_entries` | `pdfplumber` table extraction |

### Review UI fields

In addition to the parsed data, the admin can set per entry:
- `project_id` — links the VIB entry to an existing project (auto-suggested via VDE-number + fuzzy name matching)
- `project_status` — `"Planung"` or `"Bau"` (user-assigned high-level status)
- `raw_text` — directly editable in the review card before confirming

### DB models (migration `20260313001`, `20260331001`)

| Table | Description |
|---|---|
| `vib_report` | One row per imported year (drucksache_nr, report_date) |
| `vib_entry` | One row per Vorhaben; FK → vib_report + project (nullable) |
| `vib_pfa_entry` | PFA table rows; FK → vib_entry |
| `vib_draft_report` | Temporary parse result stored before user confirmation |

### Auto-suggestion matching

`tasks/vib_matching.py` — VDE-number extraction (highest confidence) + fuzzy name matching (SequenceMatcher + token overlap, threshold 0.50). Top suggestions stored in `suggested_project_ids` in the parse result.

## Routing API

Rail routes are computed and persisted in a two-step flow. `project_id` in all route endpoints is an **integer** (FK to `project.id`); `route_id` is a UUID.

### Step 1 — Calculate (no DB write)

```
POST /api/v1/routes/calculate
Body: { waypoints: [{lat, lon}, …], profile: "rail_default", options: {} }
```

Calls the routing microservice (GraphHopper), returns a GeoJSON `Feature` with `properties.cache_key`, `distance_m`, `duration_ms`, `bbox`, and `details`. Nothing is written to the database. Requires `editor` or `admin` role.

Errors:
- `422` — routing service returned no paths
- `502` — upstream routing microservice error

### Step 2 — Confirm (DB write)

```
POST /api/v1/projects/{project_id}/routes          → 201
Body: { "feature": <GeoJSON Feature from step 1> }
```

Persists the feature to the `routes` table and links it to the project. Returns `RouteOut` (`route_id`, `project_id`, `distance_m`, `duration_ms`, `bbox`, `geom_geojson`, `details`). Requires `editor` or `admin` role.

```
PUT /api/v1/projects/{project_id}/routes/{route_id}
Body: { "feature": <GeoJSON Feature from step 1> }
```

Replaces an existing route in-place. Returns `404` if the route does not belong to the project.

### Other endpoints

```
GET /api/v1/projects/{project_id}/routes?limit=50&offset=0   # list routes for a project
GET /api/v1/routes/{route_id}                                 # single route detail
```

### Caching

Routes are hashed (SHA-256) from waypoints, profile, options, and `GRAPH_VERSION`. Increment `GRAPH_VERSION` in `.env` whenever a new OSM extract is deployed to bust the cache.

### Parent GeoJSON auto-merge

When `geojson_representation` is updated on any project via `PATCH /api/v1/projects/{id}`, the CRUD layer (`crud/projects/projects.py :: recompute_parent_geojson`) automatically recomputes the `geojson_representation` of all ancestor projects as a `FeatureCollection` of their children's features. The cascade walks up the `superior_project_id` chain recursively until it reaches a root project. Sub-projects without a geometry are ignored.

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

