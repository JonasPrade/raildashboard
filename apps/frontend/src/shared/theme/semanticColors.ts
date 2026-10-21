// Every mapping from a domain term to a colour lives here (docs/DESIGN.md rule 1,
// docs/features/feature-idt-design.md → "Stufe 3"). Values are CSS variables from
// tokens.css so the dark scheme applies. No Mantine colour names.
export const PHASE_COLOR = {
    NICHT_GESTARTET: "var(--idt-seq-1)",
    VORPLANUNG: "var(--idt-seq-2)",
    GENEHMIGUNGSPLANUNG: "var(--idt-seq-3)",
    BAU: "var(--idt-seq-4)",
    IN_BETRIEB: "var(--idt-success)",
    UNBEKANNT: "var(--idt-line-strong)",
} as const;

export const TRAFFIC_COLOR = {
    FERNVERKEHR: "var(--idt-chart-1)",
    NAHVERKEHR: "var(--idt-chart-2)",
    GUETERVERKEHR: "var(--idt-chart-3)",
} as const;

export const FORECAST_SOURCE_COLOR = {
    "VIB-PFA": "var(--idt-chart-1)",
    "Fulda-Runde": "var(--idt-chart-2)",
    BVWP: "var(--idt-chart-3)",
    "Schätzung": "var(--idt-chart-4)",
} as const;

export const LANE_STATE_COLOR = {
    idle: "var(--idt-line-strong)",
    active: "var(--accent-primary)",
    done: "var(--idt-success)",
} as const;

// Anwendungsebene status rule: only red carries colour.
export const TODO_STATUS_STYLE = {
    OPEN: { color: "var(--text-muted)", weight: 400 },
    IN_PROGRESS: { color: "var(--text-strong)", weight: 400 },
    DONE: { color: "var(--text-muted)", weight: 400, check: true },
    OVERDUE: { color: "var(--text-strong)", weight: 700, underline: "var(--idt-danger)" },
} as const;

// W5: edge in the status colour, icon in ink, only critical with a red icon.
export const TEXT_CATEGORY_STYLE = {
    neutral: { edge: null, icon: "FileText", iconColor: "var(--text-muted)" },
    info: { edge: "var(--idt-cyan)", icon: "Info", iconColor: "var(--text-strong)" },
    warning: { edge: "var(--idt-warning)", icon: "TriangleAlert", iconColor: "var(--text-strong)" },
    critical: { edge: "var(--idt-danger)", icon: "OctagonAlert", iconColor: "var(--idt-danger)" },
} as const;

export const CHART_SERIES = [
    "var(--idt-chart-1)",
    "var(--idt-chart-2)",
    "var(--idt-chart-3)",
    "var(--idt-chart-4)",
    "var(--idt-chart-5)",
    "var(--idt-chart-6)",
] as const;

/** Colour for chart series beyond the six of CHART_SERIES (legend calls them "weitere"). */
export const CHART_SERIES_OVERFLOW = "var(--idt-seq-3)";

export const CHART_FURNITURE = {
    grid: "var(--idt-chart-grid)",
    axis: "var(--idt-chart-axis)",
    track: "var(--idt-chart-track)",
} as const;

// MapLibre cannot read CSS variables, so the map gets hex values of the same tokens.
export const MAP_COLOR = {
    default: "#6E50FA",
    selected: "#6E50FA",
    alternative: "#00DCFA",
    constituency: "#00373C",
    stroke: "#FFF6F0",
    danger: "#D64545",
} as const;

export const GROUP_COLOR_SWATCHES = ["#6E50FA", "#00DCFA", "#00373C", "#3A6068", "#B3A6FF", "#7FE9FB"] as const;
