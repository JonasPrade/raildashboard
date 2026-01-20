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
        title: "Project group filter",
        description:
            "The `GroupFilterDrawer` component lets users select multiple project groups." +
            " The selection is mirrored in the URL via the `group` query parameter, making it easy to share.",
        details: [
            "Fallback data until an API endpoint is connected via React Query",
            "Custom rendering of selected chips with colour indicators",
            "Extensible to cover loading and error states"
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
    "Reacht Query for server state management",
    "Mantine 8 as UI library",
    "MapLibre GL for map rendering"
];
