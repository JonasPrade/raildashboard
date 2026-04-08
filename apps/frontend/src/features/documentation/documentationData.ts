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
            "Raster tiles configured via the REACT_APP_TILE_LAYER_URL environment variable"
        ]
    },
    {
        title: "Project search",
        description:
            "Client-side full-text search across all loaded projects in both the map and the list view." +
            " The search term is stored in the `?search=` URL parameter so it persists across view switches and page reloads.",
        details: [
            "Searches project name, project number, and description (case-insensitive substring match)",
            "Map view: non-matching projects disappear from the map; result count shown in the controls panel",
            "List view: project cards filtered in-place with matching count and empty-state message",
            "Clear button (×) resets the search; term survives map ↔ list tab switches via URL param",
            "Debounced URL writes (~200 ms) to avoid flooding the browser history stack"
        ]
    },
    {
        title: "Project group filter",
        description:
            "The `GroupFilterDrawer` lets users select which project groups are shown on the map and in the list." +
            " The selection is mirrored in the URL via the `group` query parameter.",
        details: [
            "Clickable button list — one button per group with colour dot and project count",
            "Groups hidden by an admin (is_visible = false) are excluded automatically",
            "Selection persists across map ↔ list view switches via URL param"
        ]
    },
    {
        title: "Projekteigenschaften bearbeiten",
        description:
            "Editors und Admins können alle Felder eines Projekts über die Seitenleiste 'Projekt bearbeiten' ändern. " +
            "Dazu gehört jetzt auch die Zuordnung zu Projektgruppen.",
        details: [
            "MultiSelect-Feld mit allen verfügbaren Projektgruppen (gefüllt via useProjectGroups())",
            "Aktuelle Gruppen-Zuordnung wird als Initialwert aus project.project_groups geladen",
            "Änderungen werden als project_group_ids-Array per PATCH /api/v1/projects/{id} gespeichert",
            "Nur für editor/admin sichtbar"
        ]
    },
    {
        title: "Projekttexte & Dateianhänge",
        description:
            "Editors können jedem Projekttext Dateien anhängen (PDF, Word, Excel, JPEG, PNG, max. 50 MB). " +
            "Anhänge werden in einem persistenten Docker-Volume gespeichert und über einen gesicherten Download-Endpunkt ausgeliefert.",
        details: [
            "Datei-Upload per Klick (Mehrfachauswahl möglich) — beim Erstellen eines Texts oder nachträglich in der Textkarte",
            "Unterstützte Formate: PDF, Word (.doc/.docx), Excel (.xls/.xlsx), JPEG, PNG",
            "Download-Link pro Anhang; Dateiname, Typ-Icon und Dateigröße werden angezeigt",
            "Löschen mit Bestätigungsdialog (nur editor/admin)",
            "Sicherheit: MIME-Typ wird serverseitig via python-magic geprüft (nicht nur HTTP-Header); Content-Disposition: attachment verhindert XSS",
            "Nur für editor/admin sichtbar im Bearbeitungsmodus"
        ]
    },
    {
        title: "Change tracking & version history",
        description:
            "Every field edit on a project is recorded in the `change_log` / `change_log_entry` tables." +
            " Logged-in users can view a timeline of all changes; editors and admins can revert individual fields.",
        details: [
            "Timeline in ProjectDetail — date, user, old → new value per field (login-gated)",
            "\"Zurücksetzen\" button per entry reverts the field to its previous value (editor/admin only)",
            "Implemented in `features/changelog/ProjectHistorySection.tsx` + `useRevertProjectField` hook"
        ]
    },
    {
        title: "In-app documentation",
        description:
            "This page summarises features, workflows, and quality requirements and complements the README for developers.",
        details: [
            "Mandatory updates whenever features change",
            "Links to relevant scripts and entry points",
            "Structured overview for project stakeholders"
        ]
    },
    {
        title: "FinVe-Übersicht (/finves)",
        description:
            "Zeigt alle Finanzierungsvereinbarungen als ausklappbare Karten. " +
            "Für eingeloggte Nutzer (alle Rollen) zugänglich.",
        details: [
            "Suche nach Bezeichnung oder FinVe-Nr. (client-seitig, ohne Reload)",
            "Filter: Alle / Regulär / Sammel-FinVes",
            "Jede Karte zeigt FinVe-Nr., Name, Typ-Badge, Startjahr, Kosten",
            "Verknüpfte Projekte als anklickbare Mini-Cards (Link zur Projektdetailseite)",
            "Ausklappbare Budget-Diagramme: Budgetverteilung (BarChart), Kostenentwicklung (LineChart), Haushaltstiteln-Detailtabelle",
            "Sammel-FinVes erhalten violettes Badge; vorläufige FinVe-Nummern werden markiert"
        ]
    },
    {
        title: "VIB-Import (Verkehrsinvestitionsbericht)",
        description:
            "Editors and administrators can upload the annual Verkehrsinvestitionsbericht as PDF and import all Section B rail projects. " +
            "The PDF is parsed asynchronously via a Celery background task. " +
            "A card-based review step lets users inspect each Vorhaben individually before confirming.",
        details: [
            "Upload PDF + Berichtsjahr → background task starts, frontend polls every 2 s",
            "Review: one card per Vorhaben, navigate with ← / → arrows",
            "Each card shows: Kenndaten, Planungsstand, Bauaktivitäten, Teilinbetriebnahmen, PFA-Tabelle, editable Volltext",
            "Project mapping via searchable Select + confidence badge (auto-matched by VDE-number / fuzzy name)",
            "Projektstatus select: Planung or Bau per entry",
            "Route /admin/vib-import — visible for editor and admin roles only",
            "VIB entries shown in ProjectDetail under 'Verkehrsinvestitionsberichte' (tab per year, login-gated)"
        ]
    },
    {
        title: "Haushalts-Import (Anlage VWIB Teil B)",
        description:
            "Editors and administrators can upload the annual federal budget annex as PDF and import FinVe and Budget data into the database. " +
            "The PDF is parsed asynchronously via a Celery background task (pdfplumber). " +
            "A review step lets users inspect every row before confirming the import.",
        details: [
            "Upload PDF + Haushaltsjahr → background task starts, frontend polls every 2 s",
            "Review page: rows classified as Neu (green) / Änderung (yellow) / Unbekannt (red)",
            "New FinVes: project assignment via multi-select before confirming",
            "Confirm button is disabled once a parse result is already imported (double-import guard)",
            "Unbekannte Zeilen page: assign a FinVe-ID to unresolved rows",
            "Route /admin/haushalt-import — visible for editor and admin roles only",
            "Route /admin/haushalt-import/review/:parseResultId — review a specific run",
            "Route /admin/haushalt-unmatched — manage open unmatched rows"
        ]
    }
];

export const workflows: WorkflowStep[] = [
    {
        title: "Local development",
        steps: [
            "Clone the repository and install dependencies (`npm install`).",
            "Start the development server via `npm run dev`.",
            "Verify routes in the browser (`/` for the map, `/documentation` for docs).",
            "Always run `npm run build` before committing and fix any errors."
        ]
    },
    {
        title: "Maintain documentation",
        steps: [
            "Identify feature or UI changes.",
            "Update both README.md and the documentation page (adjust the 'Feature highlights' section).",
            "Extend the 'Workflows & quality' area when new scripts or processes appear.",
            "Create a pull request with a short summary and a list of executed checks."
        ]
    }
];

export const qualityGates: string[] = [
    "`npm run build` must finish without errors.",
    "Provide screenshots when UI changes are visible.",
    "Test query parameters and routing scenarios (especially `/` and `/documentation`)."
];

export const techStack: string[] = [
    "Vite 7 as build and dev server",
    "React 19 with React Router 7",
    "TypeScript 5 in strict mode",
    "React Query for server state management",
    "Mantine 8 as UI library",
    "MapLibre GL for map rendering"
];
