# Railway Dashboard Frontend

This project implements the React frontend for the railway dashboard. It is built with [Vite](https://vitejs.dev/), [TypeScript](https://www.typescriptlang.org/), and [Mantine](https://mantine.dev/) to provide a modular interface for visualising rail infrastructure projects.

> **Language note:** The codebase and developer-facing documentation are written in English, but the website UI content should be presented in German.

## Quick start

```bash
npm install
npm run dev
```

* `npm run dev` starts the development environment (Vite dev server).
* `npm run build` runs the TypeScript check (`tsc`) and creates the production build.
* `npm run preview` starts a local server to inspect the build output.

> **Note:** The scripts `npm run gen:api` and `npm run gen:zod` generate client code from an OpenAPI schema. They require a backend endpoint to be available at `http://127.0.0.1:8000/openapi.json`.

## Project structure
## Configuration

The frontend talks to a backend at `http://localhost:8000` by default. Use `VITE_API_BASE_URL` (for example in a `.env` file at the project root) to override the API base URL.

The map view expects a raster tile URL provided via `REACT_APP_TILE_LAYER_URL`. The Vite configuration accepts both `VITE_` and `REACT_APP_` prefixes, so either environment prefix can be used if you decide to migrate to `VITE_TILE_LAYER_URL` later. The map renders project routes from each project's `geojson_representation` payload, supports a click popover to navigate to `/projects/:projectId`, and syncs selected project groups via the `group` query parameter.

## Projektstruktur

```
├── public/                # Static assets (fonts, favicons, …)
├── src/
│   ├── components/        # Reusable UI building blocks (e.g. header)
│   ├── features/          # Domain-specific feature modules (map, projects, documentation …)
│   ├── lib/               # Utilities and infrastructure
│   ├── shared/            # Modules shared across features
│   ├── theme.ts           # Mantine theme configuration
│   └── router.tsx         # Route definitions
├── README.md              # This document
├── AGENT.MD               # Contribution guidelines
└── package.json           # npm scripts and dependencies
```

## Key dependencies

| Package | Purpose |
|---|---|
| `@mantine/core` | UI component library (layout, forms, modals, …) |
| `@mantine/charts` + `recharts` | Chart components (`DonutChart`, `LineChart`) used for FinVe budget visualisation. **Important:** `@mantine/charts/styles.css` must be imported in `main.tsx` — without it, `DonutChart` collapses to zero height and is invisible (its dimensions are set entirely via CSS classes, unlike `LineChart` which uses an explicit `h` prop). |
| `@tanstack/react-query` | Server-state management; all API calls go through `shared/api/queries.ts` |
| `react-router-dom` | Client-side routing |
| `axios` | HTTP client (configured in `shared/api/client.gen.ts`) |

## Notable features and components

### FinVe overview page (`features/finves/FinveOverviewPage.tsx`)

Available at `/finves` (**public — no login required**). Shows all Finanzierungsvereinbarungen as expandable cards with:
- FinVe-Nr, name, type badge (Regulär / Sammel-FinVe), "vorläufig" indicator, Aufnahme year, cost figures
- Linked projects rendered as clickable mini-cards (link to `/projects/:id`)
- Expandable budget section: same three-tab chart layout as `FinveSection.tsx` (DonutChart, LineChart, detail table)
- Client-side search (name or FinVe-Nr) and SegmentedControl filter (Alle / Regulär / Sammel-FinVes)

Data comes from `useFinves()` hook → `GET /api/v1/finves/` (returns budgets + project refs in one call).

### FinVe budget display (`features/projects/components/FinveSection.tsx`)

Shows Finanzierungsvereinbarungen linked to a project in the project detail page. Data is fetched via `useProjectFinves(projectId)` (`shared/api/queries.ts` → `GET /api/v1/projects/{id}/finves`).

Each FinVe renders as a collapsible card with three tabs:
- **Kostenentwicklung** — single-series `LineChart` of `cost_estimate_actual` per Haushaltsbericht (one data point per imported report year); Y-axis domain is max × 1.1, width 130 px (only shown for ≥ 2 budget years)
- **Budgetverteilung** — `DonutChart` showing `veranschlagt` per Haushaltstiteln for the **most recent report only**; subtitle and tab label include the report year (only shown when Haushaltstiteln data is available)
- **Haushaltbericht {year}** — detail table of the most recent budget year, split into regular and *nachrichtlich* entries

Sammel-FinVes (`is_sammel_finve = true`) render as a compact inline tag instead of the full card (no charts).

Charts use a custom `ChartLegend` component rendered below the chart SVG (avoids recharts clipping) with Mantine `ColorSwatch` + `Text`.

### BVWP assessment display (`features/projects/components/BvwpDataSection.tsx`)

Shows BVWP (Bundesverkehrswegeplan) assessment data for projects that have it. Rendered inside `ProjectDetail` after the FinVe section. Hidden entirely for projects without BVWP data (query returns `null` on 404).

Data comes from `useProjectBvwp(projectId)` → `GET /api/v1/projects/{id}/bvwp`.

Layout: Mantine `Tabs` with up to 11 groups — **Grunddaten** (NKV shown as `Badge`, priority as coloured badge), **Kosten**, **Prognose PV**, **Prognose GV**, **Nutzen PV**, **Nutzen GV**, **Weitere Nutzenwirkungen**, **Umwelt**, **Raumordnung**, **Kapazität** (congestion table with reference/plancase by time period), **Sonstiges**. Tabs with no non-null fields are hidden automatically. Float values are formatted with `toLocaleString('de-DE')`.

### Project search (`features/map/MapPage.tsx` + `MapControls.tsx`)

Available on both the map and list view at `/`. A search `TextInput` (with magnifier icon and clear button) lets users find projects by name, project number, or description via case-insensitive substring matching. All filtering is client-side — no extra API calls are made, as all project data is already in memory from `useProjectGroups()`.

- **Map view:** Non-matching projects are removed from the MapLibre GeoJSON sources. The controls panel shows a "X von Y Projekten" count while a search is active. If no project matches, a centred overlay hint is displayed.
- **List view:** Project cards are filtered in-place. The count label updates to "X von Y Projekten" and an empty-state alert is shown when nothing matches.
- **URL persistence:** The term is stored in `?search=<term>` (debounced, 200 ms, `replace: true`) so it survives map ↔ list tab switches and browser back/forward navigation.
- **Dependency added:** `@tabler/icons-react` for the search and close icons.

### Admin: Project group map settings (`features/admin/ProjectGroupsAdminPage.tsx`)

Available at `/admin/project-groups` (admin only, linked from the admin board in `/admin/users`). Lets admins configure map display behaviour per group:

- **Anzeigemodus** (`SegmentedControl`): `preconfigured` — only pre-selected groups shown on map open; `all` — all visible groups shown on map open.
- **Sichtbar** (`Switch`): per-group `is_visible` toggle — hidden groups are filtered from the map, the project list, and the group filter drawer entirely.
- **Vorausgewählt** (`Switch`): per-group `is_default_selected` toggle — disabled when mode is `all` or the group is hidden.

Settings are persisted in the `AppSettings` singleton table (backend) and fetched via `useAppSettings()` / `useUpdateAppSettings()`. The map page reads `map_group_mode` on load; explicit `?group=` URL param always takes precedence.

### Haushalt PDF import (`features/haushalt-import/`)

Multi-step import workflow for federal budget PDFs. The `ReviewTable` shows auto-suggested project assignments (marked with ✦) computed during the Celery parse task via fuzzy name matching. The Projektzuordnung column has a minimum width of 320 px.

`HaushaltsGuidePage.tsx` (`/admin/haushalt-import/guide`) provides a step-by-step user guide (accordion format) with troubleshooting FAQ. Linked from both the import page and the review page.

## Development conventions

* **Stay strict with TypeScript:** New modules should embrace type safety (avoid `any`).
* **Feature folder structure:** Functional areas (e.g. map, projects, documentation) live in dedicated folders under `src/features`.
* **Separation of concerns:** Put UI components in `components/`, technical helpers in `lib/`, and global types in `types.ts` or `shared/`.
* **Mantine components:** Prefer Mantine for layout and UI work, and keep theme colours consistent (`theme.ts`).
* **Routing:** Register new pages as children of the shared `Layout` component in `router.tsx`.
* **Keep documentation current:** Any functional or visual change must be reflected in both developer- and user-facing docs (README, in-app documentation page).

## Documentation inside the app

Navigate to `/documentation` to access the embedded documentation page. It outlines the key features, workflows, and quality requirements. Update this page whenever the functional scope changes.

## Docker (production)

The frontend ships with a multi-stage `Dockerfile` (`apps/frontend/Dockerfile`):

- **Builder stage** — runs `npm ci` and `npm run build` on `node:20-slim`. The `VITE_API_BASE_URL` build argument is set to `""` so API calls use a relative path (`/api/...`).
- **Runtime stage** — serves the compiled `dist/` folder via `nginx:alpine`. The custom `nginx.conf` handles SPA routing (`try_files $uri /index.html`) and proxies `/api/` to the backend container.

Build and start via the repository root:
```bash
make docker-prod-build
make docker-prod-up
```

## Quality checks

Run at least the following check before committing:

```bash
npm run build
```

Feel free to add project-specific tests or linters as they become available. Document the executed checks in the pull request.

## Licence

The project is currently internal. Add a licence file once the project is ready for public release.

---

See the **repository root** for the project-wide `README.md`, `AGENT.md`, `Makefile`, and `.env.example`.
