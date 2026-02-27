export type FeatureHighlight = {
    title: string;
    description: string;
    details?: string[];
};

export type WorkflowStep = {
    title: string;
    steps: string[];
};

export const featureHighlights: FeatureHighlight[] = [
    {
        title: "Interactive map view",
        description:
            "MapLibre-based map with Mantine overlays for controls such as filters." +
            " The base map uses a configurable raster tile source so additional layers or data sources can be integrated later on.",
        details: [
            "Filter drawer for project groups including URL synchronisation",
            "Mantine components for buttons, panels, and layout",
            "Project route geometries rendered from each project's `geojson_representation` field",
            "Hover interactions that highlight routes and show pointer feedback",
            "Route click popover with project title and direct navigation action",
            "Raster tiles configured via the VITE_TILE_LAYER_URL environment variable"
        ]
    },
    {
        title: "Map rendering & visual controls",
        description:
            "Project routes and points are rendered from GeoJSON data with configurable visual settings." +
            " Sliders in the map controls overlay adjust rendering in real time without a page reload.",
        details: [
            "Line width slider (1–10 px, default 4 px)",
            "Point size slider (1–15 px, default 5 px) for circle features",
            "MultiLineString geometry with `line-cap: round` eliminates visible gaps between segments",
            "Separate Circle layer for point features extracted from project GeoJSON",
            "Group colour applied per project; map sources updated via `source.setData()` without re-registering layers"
        ]
    },
    {
        title: "Map / list tab toggle",
        description:
            "Map and project list are unified on the root route (`/`). A segmented control switches between the two views.",
        details: [
            "Active view persisted in URL: `?view=map` or `?view=list` — views are bookmarkable and shareable",
            "\"Zur Karte\" button in the project detail view navigates back to the map, preserving group filters",
            "Former `/projects` route redirects to `/?view=list` for backward compatibility",
            "List view shows a single-select group picker, group info card, and a responsive project grid"
        ]
    },
    {
        title: "Project group filter & URL persistence",
        description:
            "The `GroupFilterDrawer` component lets users select one or more project groups." +
            " The selection is mirrored in the URL via the `group` query parameter.",
        details: [
            "Multi-select mode in map view; single-select in list view",
            "Selected groups shown as removable pills with colour indicators",
            "Group colour dot and project-count badge for each option",
            "Apply / Cancel actions; first group auto-selected when switching to list view if none is active",
            "Group IDs persisted as comma-separated values: `?group=1,2,3`"
        ]
    },
    {
        title: "Top-level project filter",
        description:
            "A \"Nur Hauptprojekte\" toggle in the map controls filters the view to show only projects without a parent project.",
        details: [
            "Filters on `superior_project_id IS NULL` — reduces visual clutter when exploring the high-level landscape",
            "Available in both map and list views",
            "Applied on top of any active group filter"
        ]
    },
    {
        title: "Map popup & project summary card",
        description:
            "Clicking a route or point on the map opens a popup with a compact `ProjectSummaryCard`." +
            " The card is a reusable component shared with the project detail page and sub-project lists.",
        details: [
            "Shows project name, project number badge, and a two-line description excerpt",
            "Active traffic categories as colour-coded badges (Fernverkehr, Nahverkehr, Güterverkehr)",
            "Active feature badges grouped by category (Streckenausbau, Bahnhöfe, Signaltechnik, Elektrifizierung, Sonstiges)",
            "Clicking the card navigates to the full project detail page",
            "Popup dismissed on outside click"
        ]
    },
    {
        title: "Project detail view",
        description:
            "The project detail page provides a comprehensive two-column layout: a narrow details panel on the left and the project map on the right.",
        details: [
            "Header with project name, project number badge, and navigation buttons (map / project list)",
            "Left panel: project metrics (length, speed, ETCS, station counts), traffic category badges, active feature badges grouped by category",
            "Right panel: embedded map showing the project's own geometry plus all sub-projects (clickable)",
            "Description and justification cards rendered below the two-column section",
            "Parent project and sub-projects each displayed with `ProjectSummaryCard` in collapsible sections",
            "Project texts section and version history section (authenticated users only)"
        ]
    },
    {
        title: "Project editing",
        description:
            "Authenticated users with the `editor` or `admin` role can edit all project fields in a right-side drawer." +
            " The form detects unsaved changes and validates input before submitting.",
        details: [
            "Stammdaten: name, project number, length (km), description, justification",
            "Verkehrsarten: Fernverkehr / Nahverkehr / Güterverkehr toggle switches",
            "Streckenausbau: NBS, ABS, second/third/fourth track, curve, speed increase, new Vmax, tunnel structural gauge, tilting",
            "Bahnhöfe & Infrastruktur: new station, platforms, junction/overtaking stations, depot, level-free access, double occupancy, buffer track, overpass, noise barriers, railroad crossings, GWB",
            "Signaltechnik & Digitalisierung: ETCS with level selector, ESTW, DSTW, block increase, switches, flying junctions",
            "Elektrifizierung & Energie: electrification, optimised electrification, charging stations, battery/H2/E-Fuel, fuel station count",
            "Sonstiges: SGV 740 m, Sanierung, Closure",
            "All changes sent via `PATCH /api/v1/projects/{id}` and automatically recorded in the change log"
        ]
    },
    {
        title: "Project text management",
        description:
            "Each project can have an arbitrary number of associated texts (press releases, background articles, etc.)." +
            " Texts can be restricted to authenticated users or made publicly visible.",
        details: [
            "Text types are user-defined categories; new types can be created inline via a modal",
            "Each text has a header, type, optional body content, optional weblink, and optional logo URL",
            "Create and edit via modal form; requires `editor` or `admin` role",
            "Visibility flag: texts can be marked as login-only or publicly accessible",
            "Section hidden from anonymous users if no public texts exist; empty state shown to editors",
            "All text changes recorded in the project change log"
        ]
    },
    {
        title: "Authentication & authorisation",
        description:
            "The app uses HTTP Basic Auth with three roles. Credentials are stored in the browser and restored on reload." +
            " Anonymous users can read all public data; write operations and sensitive sections require login.",
        details: [
            "\"Anmelden\" button in the header opens a login modal; credentials sent as HTTP Basic Auth",
            "Credentials persisted in localStorage; session restored via `GET /api/v1/users/me` on app start",
            "Three roles: `viewer` (read-only), `editor` (create/edit projects and texts), `admin` (full access + user management)",
            "Edit buttons, create actions, and version history hidden from unauthenticated visitors",
            "API interceptor triggers the login modal on 401/403 responses without forcing a page redirect",
            "\"Abmelden\" button in the header clears credentials and resets state"
        ]
    },
    {
        title: "User management",
        description:
            "Administrators can manage all application users through a dedicated page at `/admin`." +
            " Access is restricted to users with the `admin` role.",
        details: [
            "User table: username, role, creation date; current user marked as \"(ich)\"",
            "Create new user (username + initial password)",
            "Change role via inline dropdown (viewer / editor / admin)",
            "Reset or change password via dedicated modal",
            "Delete user with confirmation prompt",
            "Non-admin users are redirected away from `/admin`"
        ]
    },
    {
        title: "Change tracking",
        description:
            "Every project update is recorded in a structured change log that captures which fields changed," +
            " the old and new values, the responsible user, and the timestamp.",
        details: [
            "Backend: `ChangeLog` and `ChangeLogEntry` tables; each PATCH creates one entry per changed field",
            "`PATCH /api/v1/projects/{id}` requires `editor` or `admin` role",
            "`GET /api/v1/projects/{id}/changelog` returns the full audit trail",
            "Frontend: `ProjectHistorySection` renders a unified timeline of project-field and text changes (newest first)",
            "Each entry shows timestamp, action badge (CREATE / PATCH / REVERT / DELETE), username, and old → new values",
            "Version history visible only to authenticated users",
            "German display labels for all 40+ tracked project fields; booleans formatted as Ja / Nein"
        ]
    },
    {
        title: "Routing backend",
        description:
            "The backend integrates a GrassHopper / pgRouting microservice that computes rail route geometries between operational points.",
        details: [
            "Routing service configured via the `ROUTING_BASE_URL` environment variable",
            "Computed routes cached in PostGIS using a graph-version hash to keep the cache consistent with the deployed service",
            "Foundation for the planned \"Route berechnen\" feature in the project detail view (see roadmap)"
        ]
    },
    {
        title: "In-app documentation",
        description:
            "This page summarises features, workflows, and quality requirements and complements the README for developers.",
        details: [
            "Must be updated whenever the user-facing feature scope changes",
            "Links to relevant scripts and entry points",
            "Structured overview for project stakeholders"
        ]
    }
];

export const workflows: WorkflowStep[] = [
    {
        title: "Local development",
        steps: [
            "Clone the repository and install all dependencies: `make install`.",
            "Start backend (port 8000) and frontend (port 5173) concurrently: `make dev`.",
            "Verify routes: `/` (map), `/documentation` (this page), `/projects/:id` (detail), `/admin` (admin, requires admin role).",
            "Always run `npm run build` before committing and resolve any TypeScript errors."
        ]
    },
    {
        title: "Adding or modifying a project field",
        steps: [
            "Update the SQLAlchemy model and create an Alembic migration: `make migrate-create MSG='...'`.",
            "Update the Pydantic schema (`ProjectUpdate`) and the CRUD layer.",
            "Run `make gen-api` to regenerate the frontend API client (backend must be running).",
            "Update `ProjectEdit.tsx` (form type + initial values + field), `ProjectDetail.tsx` (`createUpdatePayload()`), and `queries.ts` (`ProjectUpdatePayload`).",
            "Add the new field to the German label map in `ProjectHistorySection.tsx` so it appears correctly in the change log."
        ]
    },
    {
        title: "Maintain documentation",
        steps: [
            "Identify feature or UI changes.",
            "Update `apps/frontend/README.md`, `apps/backend/README.md`, and this page (`documentationData.ts`) to reflect the change.",
            "Extend the 'Workflows & quality' area when new scripts or processes appear.",
            "Create a pull request with a short summary and a list of executed checks."
        ]
    }
];

export const qualityGates: string[] = [
    "`npm run build` must finish without errors before every commit.",
    "Run `make test-backend` after every Python change.",
    "Run `make gen-api` after every OpenAPI schema change (backend must be running).",
    "Provide screenshots (1440 px wide) when UI changes are visible.",
    "Test URL-param scenarios: `?view=`, `?group=`, project detail navigation."
];

export const techStack: string[] = [
    "Vite 7 as build and dev server",
    "React 19 with React Router 7",
    "TypeScript 5 in strict mode",
    "React Query (TanStack) for server state management",
    "Mantine 8 as UI library",
    "MapLibre GL for map rendering",
    "FastAPI + SQLAlchemy + PostGIS (backend)",
    "HTTP Basic Auth with PBKDF2 password hashing; roles: viewer / editor / admin"
];
