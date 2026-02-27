# Railway Dashboard Frontend

This project implements the React frontend for the railway dashboard. It is built with [Vite](https://vitejs.dev/), [TypeScript](https://www.typescriptlang.org/), and [Mantine](https://mantine.dev/) to provide a modular interface for visualising and managing rail infrastructure projects.

> **Language note:** The codebase and developer-facing documentation are written in English, but the website UI content is presented in German.

## Quick start

```bash
npm install
npm run dev
```

* `npm run dev` starts the Vite dev server (port 5173 by default).
* `npm run build` runs the TypeScript check (`tsc`) and creates the production build.
* `npm run preview` starts a local server to inspect the build output.

> **Note:** `npm run gen:api` and `npm run gen:zod` generate client code from the backend OpenAPI schema. They require the backend to be running at `http://127.0.0.1:8000/openapi.json`.

## Configuration

| Variable | Description |
|---|---|
| `VITE_API_BASE_URL` | Backend API base URL (default: `http://localhost:8000`) |
| `VITE_TILE_LAYER_URL` | Raster tile URL for the map background |

Create a `.env` file in the repository root and set these variables. See `.env.example` for a reference.

## Project structure

```
public/                  # Static assets (fonts, favicons, …)
src/
├── components/          # Shared UI building blocks (header, error boundary, …)
├── features/
│   ├── admin/           # User management page (admin-only)
│   ├── auth/            # Login modal, auth context
│   ├── changelog/       # ProjectHistorySection — change log timeline
│   ├── documentation/   # In-app documentation page
│   ├── map/             # MapView, MapControls, GroupFilterDrawer, MapPage
│   └── projects/        # ProjectDetail, ProjectEdit, ProjectSummaryCard,
│                        # ProjectTextsSection, ProjectCard
├── lib/                 # Auth helpers, API client config, React Query setup
├── shared/              # Generated API client (do not edit by hand), cross-feature utils
├── theme.ts             # Mantine theme configuration (custom colour "petrol")
└── router.tsx           # Route definitions
```

## Application routes

| Route | Component | Access |
|---|---|---|
| `/` | `MapPage` (map + list toggle via `?view=`) | Public |
| `/projects/:projectId` | `ProjectDetail` | Public |
| `/admin` | `UsersPage` | `admin` role only |
| `/documentation` | `DocumentationPage` | Public |
| `/projects` | — | Redirects to `/?view=list` |

## Implemented features

### Map & visualisation
* **Interactive map view** — MapLibre-based, renders project routes and points from each project's `geojson_representation`
* **Line width & point size sliders** — configurable in real time (default line: 4 px, default point: 5 px)
* **MultiLineString rendering** — `line-cap: round` eliminates gaps between segments; separate Circle layer for point features
* **Map popup** — clicking a route or point opens a `ProjectSummaryCard` with project number, description, and feature badges

### Navigation & filtering
* **Map / list tab toggle** — unified root route (`/`); active view in URL (`?view=map` or `?view=list`)
* **Project group filter** — multi-select drawer; selection persisted as `?group=1,2,3` in the URL
* **Top-level project filter** — "Nur Hauptprojekte" toggle filters to `superior_project_id IS NULL`

### Project detail
* **Two-column layout** — project metrics and feature badges left, embedded map right
* **Parent & sub-project cards** — each displayed with `ProjectSummaryCard` in collapsible sections; sub-projects clickable on the embedded map
* **Project editing** — right-side drawer with all project fields across 7 groups (Stammdaten, Verkehrsarten, Streckenausbau, Bahnhöfe, Signaltechnik, Elektrifizierung, Sonstiges); changes sent via `PATCH`

### Content & texts
* **Project text management** — create, edit, and delete texts per project; user-defined text types; visibility flag (public / login-only)
* **Change tracking timeline** — `ProjectHistorySection` shows a unified audit trail of field changes and text changes; visible to authenticated users only

### Authentication & user management
* **HTTP Basic Auth** — login modal in header; credentials stored in `localStorage` and restored on reload
* **Role-based access** — `viewer` (read-only), `editor` (create/edit), `admin` (full access + user management)
* **User management page** (`/admin`) — create users, change roles, reset passwords, delete users; admin-only

## Development conventions

* **TypeScript strict mode:** Avoid `any`; use `unknown` with type guards for temporarily untyped values.
* **Feature folder structure:** Functional areas live in dedicated folders under `src/features/`.
* **State management:** React Query for server data; URL search params for shareable filter state; `useState` for local UI state. Do **not** introduce Zustand or Redux.
* **React Query naming:** queries → `use<Resource>()`, mutations → `use<Verb><Resource>()`.
* **Mantine components:** Prefer Mantine for layout and UI; keep theme overrides in `theme.ts`.
* **Generated files:** Never edit `src/shared/api/types.gen.ts` or `src/shared/api/client.gen.ts` by hand — regenerate via `make gen-api`.
* **Project field sync:** Whenever a project field is added or removed, update `ProjectEdit.tsx`, `ProjectDetail.tsx`, `queries.ts`, the backend schema, and the label map in `ProjectHistorySection.tsx` in the same change.

## Documentation inside the app

Navigate to `/documentation` to access the embedded documentation page. It provides an up-to-date overview of all features, workflows, and quality requirements. **Update `src/features/documentation/documentationData.ts` whenever the functional scope changes.**

## Quality checks

Run at minimum before every commit:

```bash
npm run build    # TypeScript check + production bundle
npm run lint     # ESLint
npm run test     # Vitest unit/integration tests
```

Attach screenshots (PNG/WebP, 1440 px width) to pull requests that include visible UI changes.

## Licence

Internal project. A licence file will be added before public release.

---

See the **repository root** for the project-wide `README.md`, `AGENT.md`, `Makefile`, and `.env.example`.
