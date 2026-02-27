# Architecture

## Overview

Schienendashboard is a full-stack web application with a FastAPI backend and a React frontend, both living in the `apps/` directory of the monorepo.

```
apps/
├── backend/   # FastAPI + SQLAlchemy + PostGIS (Python)
└── frontend/  # React + Vite + Mantine + MapLibre (TypeScript)
```

The frontend communicates with the backend exclusively via the REST API. Types are generated automatically from the OpenAPI schema (`make gen-api`).

---

## Backend Structure

The backend follows a classical layered architecture to separate responsibilities.


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


### 1. API Layer (`api/`)
- Provides endpoints using FastAPI
- Versioned under `/api/v1`
- Endpoints grouped by topic (projects, documents, routing, etc.)

### 2. Schema Layer (`schemas/`)
- Defines input and output models using Pydantic
- Decouples API data representation from database structure
- Provides typing, validation, and auto-documentation

### 3. CRUD Layer (`crud/`)
- Contains read and write database operations (e.g. `get_project`, `create_project`)
- Clean abstraction layer between API and database

### 4. Database Layer (`models/`)
- SQLAlchemy ORM models for all core entities
- Uses `geoalchemy2` for geodata (PostGIS)

### 5. Configuration & Infrastructure (`core/`)
- Database connection (SQLAlchemy engine, session)
- Environment variables loaded via Pydantic Settings from the repo-root `.env`

### 6. Service Layer (`services/`)
- Parser-related tasks and raw data transformation
- e.g. PDF processing, RailML import

### 7. Entry Point (`main.py`)
- Initialises the FastAPI app
- Registers API routers
- Configures global middleware (CORS, logging)

### Data folder
All changeable runtime data lives in `apps/backend/data/`.

### Authentication & authorisation

The backend uses **HTTP Basic Auth**. The `AuthRouter` class (`routing/auth_router.py`) automatically enforces authentication on all non-GET endpoints. Use it instead of the standard `APIRouter` for any router that handles write operations.

Roles: `viewer` (read-only), `editor` (can write projects/routes), `admin` (full access, user management). Protect endpoints with `Depends(require_roles(UserRole.editor))` from `core/security.py`.

**Visibility of sensitive data:** Version history (changelog) and any data containing usernames or internal change records must **only be visible to logged-in users**. Anonymous visitors (unauthenticated viewers) must not see this data. This rule applies everywhere change tracking is displayed, not only in `ProjectHistorySection`.

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

## Frontend Structure

The frontend is a feature-oriented React application.

```
src/
├── features/     # Domain-specific modules (map, projects, documentation …)
├── components/   # Shared UI building blocks (header, error boundary)
├── shared/       # Cross-feature utilities and generated API client
├── lib/          # Infrastructure (API client config, React Query setup, auth)
├── theme.ts      # Mantine theme configuration
└── router.tsx    # Central route definitions
```

### Key technology choices
| Concern | Library |
|---|---|
| UI framework | Mantine |
| Map rendering | MapLibre GL |
| Server state | TanStack React Query |
| Routing | React Router |
| Build tool | Vite |
| Type safety | TypeScript strict mode |

New functional areas go into `src/features/<name>/`. Shared UI components used by two or more features go into `src/components/`.

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

### Project field sync rule

**Whenever a project field is added, renamed, or removed** (in the SQLAlchemy model, Pydantic schema, or `ProjectSchema`), all of the following files must be updated in the same change:

| File | What to update |
|---|---|
| `features/projects/ProjectEdit.tsx` | `ProjectEditFormValues` type, `createInitialValues()`, form field in the correct group |
| `features/projects/ProjectDetail.tsx` | `createUpdatePayload()` |
| `shared/api/queries.ts` | `ProjectUpdatePayload` type |
| `dashboard_backend/schemas/projects/project_update_schema.py` | `ProjectUpdate` Pydantic schema |

### Code quality (frontend)

Before committing, run:

```bash
npm run build       # TypeScript check + production build
npm run lint        # ESLint
npm run test        # Vitest unit/integration tests
```

- Apply `useMemo`/`useCallback` for expensive computations and to stabilise references passed as deps.

