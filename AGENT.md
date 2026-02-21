# Contributor Guide – Schienendashboard

This file applies to the entire repository. Read it before making any substantial change.

> **Default language:** English. Write code, comments, documentation, commit messages, and PR descriptions in English. UI strings displayed to end users are in German.

---

## Repository structure

```
apps/
├── backend/   # FastAPI + SQLAlchemy + PostGIS
└── frontend/  # React + Vite + Mantine + MapLibre
docs/          # Architecture, data models, roadmap
Makefile       # Common dev tasks (run `make help`)
.env.example   # All required environment variables with descriptions
```

Changes that span both apps (e.g. a new API contract) require coordinated updates to both sides. Always verify the full roundtrip works before opening a PR.

---

## Development environment

### Quick start

```bash
cp .env.example .env          # fill in DATABASE_URL and REACT_APP_TILE_LAYER_URL at minimum
make install                  # create Python venv + npm install
make migrate                  # apply Alembic migrations
make dev                      # start backend (port 8000) + frontend (port 5173) concurrently
```

### Make targets reference

| Target | Description |
|---|---|
| `make dev` | Start backend + frontend concurrently (Ctrl-C stops both) |
| `make dev-backend` | Start uvicorn with --reload |
| `make dev-frontend` | Start Vite dev server |
| `make test` | Run all tests (backend + frontend) |
| `make test-backend` | Run pytest |
| `make test-frontend` | Run Vitest |
| `make lint` | Run all linters |
| `make migrate` | Apply all pending Alembic migrations |
| `make migrate-create MSG='...'` | Create a new Alembic revision |
| `make list-users` | List all users with their roles |
| `make create-user USERNAME=… ROLE=…` | Create a new user (`viewer`/`editor`/`admin`) |
| `make change-password USERNAME=…` | Change an existing user's password |
| `make gen-api` | Regenerate frontend API client (backend must be running) |
| `make build` | Production build |
| `make clean` | Remove build artifacts and caches |

### Environment variables

Copy `.env.example` to `.env` and fill in values. Required variables:

| Variable | Used by | Notes |
|---|---|---|
| `DATABASE_URL` | Backend | `postgresql+psycopg2://user:pw@host:port/db` |
| `REACT_APP_TILE_LAYER_URL` | Frontend | Raster tile URL for map background |
| `VITE_API_BASE_URL` | Frontend | Defaults to `http://localhost:8000` |
| `ROUTING_BASE_URL` | Backend | GraphHopper instance URL |
| `RINF_API_URL` / `RINF_USERNAME` / `RINF_PASSWORD` | Backend | ERA RINF API credentials |

> ⚠️ **Never modify or overwrite `.env`.** It contains personal local settings. Only read from it.

### Test environment setup

`make test-backend` sets `ENVIRONMENT=test` automatically, which tells the backend to load `.env.test` instead of `.env`. There are two files to create (both are gitignored):

| File | Loaded by | Setup |
|---|---|---|
| `.env.test` (repo root) | pydantic settings via `config.py` | `cp .env.test.example .env.test` |
| `apps/backend/env.test` (no dot!) | `tests/db_related_tests/conftest.py` directly | `cp apps/backend/env.test.example apps/backend/env.test` |

In both files, set `DATABASE_URL` to the test database connection string. The URL **must contain the word `test`** — the test suite enforces this to prevent accidental writes to a production database.

**Test database tiers:**
- `tests/api/` — SQLite in-memory, no setup needed, runs without `.env.test`
- `tests/db_related_tests/` — real PostgreSQL + PostGIS, requires both files above

---

## How to approach tasks

Before writing any code:
1. **Read the relevant existing layer** (endpoint, CRUD function, component) — understand the pattern before adding to it.
2. **New API route checklist:** router endpoint + Pydantic schema + CRUD function + test + `make gen-api` to sync the frontend client.
3. **New frontend feature checklist:** component in `src/features/<name>/` + query/mutation hook in `queries.ts` + route in `router.tsx` if it's a page.
4. **Never add a dependency** without first checking whether an existing library already covers the need.

---

## Backend guidelines (`apps/backend/`)

### Architecture

The codebase follows a strict separation of concerns. Every new feature touches all relevant layers:

| Layer | Location | Responsibility |
|---|---|---|
| Routers | `dashboard_backend/api/v1/endpoints/` | HTTP endpoints, request validation |
| Schemas | `dashboard_backend/schemas/` | Pydantic request/response models |
| CRUD | `dashboard_backend/crud/` | Database queries via SQLAlchemy |
| Models | `dashboard_backend/models/` | SQLAlchemy ORM models |
| Services | `dashboard_backend/services/` | Business logic, external client calls |

- Use **type hints** in all new or modified Python functions.
- Use **SQLAlchemy ORM** for all database interactions – never raw SQL strings, never SQLite.
- The database is **PostgreSQL with the PostGIS extension**. All spatial data uses **EPSG:4326 (WGS 84)**. Use `geoalchemy2.types.Geometry` for geometry columns, e.g. `Geometry(geometry_type='MULTILINESTRING', srid=4326)`.
- Group related database tables in a dedicated subdirectory (e.g. `models/osmr/`, `models/eba_data/`) to keep domain boundaries clear.

### Authentication & authorisation

The backend uses **HTTP Basic Auth**. The `AuthRouter` class (`routing/auth_router.py`) automatically enforces authentication on all non-GET endpoints. Use it instead of the standard `APIRouter` for any router that handles write operations.

Roles: `viewer` (read-only), `editor` (can write projects/routes), `admin` (full access, user management). Protect endpoints with `Depends(require_roles(UserRole.editor))` from `core/security.py`.

### Error handling (backend)

- `404` for missing resources, `400` for invalid input, `409` for conflicts (e.g. duplicate username), `403` for authorisation failures.
- Use `HTTPException` directly; do not wrap in custom exception classes unless there's a cross-cutting reason.

### Database migrations

Every model change requires an Alembic migration:

```bash
make migrate-create MSG="short description"
make migrate
```

Never modify existing migration files. Always create a new revision.

> **PostGIS caveat:** Alembic autogenerate does not detect changes to PostGIS geometry columns reliably. Write the `op.add_column` / `op.alter_column` calls manually for geometry fields.

### Testing (backend)

```bash
make test-backend
```

- Run tests for every Python change (documentation-only changes are exempt).
- For database-dependent tests, use a dedicated test database and set `ENVIRONMENT=test` so `.env.test` is loaded.
- Extend `tests/api/` immediately whenever you add or change an API route.

### Data import scripts

- Place new import scripts under `scripts/` with an `argparse`-based CLI.
- Document new import paths in `docs/` and add a short example to `apps/backend/README.md`.

---

## Frontend guidelines (`apps/frontend/`)

### Architecture

```
src/
├── features/     # Domain-specific feature modules (map, projects, documentation …)
├── components/   # Shared UI building blocks (header, error boundary)
├── shared/       # Cross-feature utilities and generated API client
├── lib/          # Infrastructure (API client config, React Query setup, auth)
├── theme.ts      # Mantine theme configuration (custom colours incl. "petrol")
└── router.tsx    # Central route definitions
```

- New functional areas go into `src/features/<name>/`.
- Shared UI components (used by two or more features) go into `src/components/`.
- Global types go into `src/types/` or `shared/`. Feature-specific types stay local.

### TypeScript

- **Avoid `any`.** Use `unknown` for temporarily untyped values; add type guards to refine them.
- Enable strict mode; do not disable TypeScript checks with `@ts-ignore` without a comment explaining why.

### UI components

- Use **Mantine** for layout and UI work. Keep theme overrides in `theme.ts`. The custom colour `"petrol"` is available for primary actions.
- Extract recurring patterns into custom components under `src/components/`.

### Routing

- Register new pages in `src/router.tsx` as children of the shared `Layout` component.
- Use `React.lazy()` + `Suspense` for routes with heavy bundles.

### State management

| State type | Tool | Where |
|---|---|---|
| Server data (fetched from API) | **React Query** | Hooks in `src/shared/api/queries.ts` |
| Filter / view state (shareable via URL) | **URL search params** (`useSearchParams`) | Component or page level |
| Local UI state (modal open, slider value) | **React `useState`** | Component level |

Do **not** introduce Zustand or Redux. The project intentionally avoids client-side global stores.

**React Query hook naming:**
- Queries: `use<Resource>` — e.g. `useProjects()`, `useProjectGroups()`
- Mutations: `use<Verb><Resource>` — e.g. `useCreateProject()`, `useUpdateProject()`

### Error handling (frontend)

- Use Mantine `Alert` (variant `"light"`, color `"red"`) for inline error states in forms and data views.
- Use React Query's `isError` / `error` fields — do not catch fetch errors manually.
- Do not use `console.error` in production code paths.

### Map (MapLibre)

- All map sources are registered once on map init; data is updated via `source.setData()`.
- Source naming: `"project-routes"` (LineString), `"project-points"` (Point). Layer naming: `"project-routes-line"`, `"project-points-circle"`.
- All GeoJSON uses **EPSG:4326**. Feature properties are the only channel for per-feature metadata in click/hover handlers (MapLibre serialises them to plain JSON).
- Do not store extra state in MapLibre feature properties beyond what's needed for rendering and popups.

### Generated files — do not edit manually

`src/shared/api/types.gen.ts` and `src/shared/api/client.gen.ts` are auto-generated from the backend OpenAPI schema. **Never edit them by hand.** After changing the backend schema, regenerate:

```bash
# Backend must be running at http://localhost:8000
make gen-api
```

### Code quality (frontend)

Before committing, run:

```bash
npm run build       # TypeScript check + production build
npm run lint        # ESLint
npm run test        # Vitest unit/integration tests
```

- Apply `useMemo`/`useCallback` for expensive computations and to stabilise references passed as deps.

---

## Git workflow

- **Branches:** `feature/<summary>`, `fix/<bug-id>`, `docs/<topic>`, `refactor/<area>`.
- **Strategy:** `master` stays stable and deployable. Branch directly from `master`.
- **Merges:** Squash-merge feature branches. Rebase your branch onto the latest `master` before submitting a PR.
- **Commit messages:** Follow Conventional Commits:
  - `feat(map): add project route hover effect`
  - `fix(api): correct bounding-box serialisation`
  - `docs: update OSM import instructions`
  - `chore: add Makefile`

---

## Documentation

- Keep `README.md` (root) up to date for project-wide setup and workflow changes.
- Keep `apps/backend/README.md` up to date for backend-specific setup, routing API, and data imports.
- Keep `apps/frontend/README.md` up to date for frontend-specific setup and project structure.
- Update `apps/frontend/src/features/documentation/DocumentationPage.tsx` (the in-app docs) whenever the user-facing feature scope changes.
- Project-wide architecture, data models, and the roadmap live in `docs/` (repo root).
- Backend-specific implementation details live in `apps/backend/docs/`.

---

## Pull requests

**PR description template:**

```markdown
## Summary
- ...

## Testing
- [ ] `make test-backend` / `make test-frontend`
- [ ] Manual smoke test
- [ ] `make gen-api` run if OpenAPI schema changed
- [ ] Documentation updated (README + in-app docs if applicable)
- [ ] Screenshots/demo attached (for UI changes)
- [ ] Breaking changes documented
```

- For UI changes, attach screenshots (PNG/WebP, 1440 px width) or a short screen recording (≤ 2 min).
- Place screenshots under `docs/screenshots/<feature>/` with a date or commit hash in the filename.
