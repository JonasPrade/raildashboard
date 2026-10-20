/**
 * Pure helpers for the Infraplan views (docs/features/feature-infraplan-import.md):
 * labels, number formatting, year-over-year deltas per measure and the shaping
 * of KPI values into chart rows. No React here, so everything is unit-tested.
 */

import type {
    InfraplanParsedRow,
    InfraplanProjectEntry,
    InfraplanPublicKpi,
} from "../../shared/api/queries";

export const SECTION_SHORT: Record<string, string> = {
    BP_A: "BP Teil A",
    BP_B: "BP Teil B",
    BP_C: "BP Teil C",
    BP_D: "BP Teil D",
    GVFG_A: "GVFG Kat. A",
    GVFG_C: "GVFG Kat. C",
    INVKG: "InvKG",
};

export const PARL_LABEL: Record<string, string> = {
    ABGESCHLOSSEN: "abgeschlossen",
    LAEUFT: "läuft",
    VORGESEHEN: "vorgesehen",
    NICHT_VEREINBART: "nicht vereinbart",
};

export const SOURCE_LABEL: Record<string, string> = {
    NUMBER: "Projektnummer",
    FUZZY: "Namensähnlichkeit",
    MANUAL: "manuell",
    AGENT: "KI-Agent",
};

export const SOURCE_COLOR: Record<string, string> = {
    NUMBER: "green",
    FUZZY: "yellow",
    MANUAL: "blue",
    AGENT: "grape",
};

export const REASON_LABEL: Record<string, string> = {
    NUMBER: "Nummer",
    GVFG_KEY: "GVFG-Schlüssel",
    FUZZY: "Name",
};

export const KPI_KIND_LABEL: Record<string, string> = {
    STEUERUNG: "Steuerungskennzahlen",
    INFORMATION: "Informationskennzahlen",
};

export const KPI_CATEGORY_LABEL: Record<string, string> = {
    AUS_NEUBAU: "Aus- und Neubau",
    BESTANDSNETZ: "Bestandsnetz",
    UEBERGEORDNET: "Übergeordnet",
};

/** "1.234,5" — Infraplan amounts are in Mio. €; dash for null. */
export function formatMio(value: number | null | undefined, digits = 1): string {
    if (value === null || value === undefined || !Number.isFinite(value)) return "–";
    return value.toLocaleString("de-DE", { minimumFractionDigits: 0, maximumFractionDigits: digits });
}

/** "+12 %" / "−3 %" with a real minus sign; null when there is no base. */
export function formatPercentChange(from: number, to: number): string | null {
    if (!from) return null;
    const pct = Math.round(((to - from) / from) * 100);
    if (pct === 0) return "±0 %";
    return `${pct > 0 ? "+" : "−"}${Math.abs(pct)} %`;
}

/** Percentage 0..1 → "92 %". */
export function formatConfidence(confidence: number): string {
    return `${Math.round(confidence * 100)} %`;
}

// ---------------------------------------------------------------------------
// Review: filtering draft rows
// ---------------------------------------------------------------------------

export type RowFilter = {
    /** Section key or "ALL". */
    section: string;
    onlyUnassigned: boolean;
    search: string;
};

export function isAssigned(row: Pick<InfraplanParsedRow, "project_ids">): boolean {
    return (row.project_ids ?? []).length > 0;
}

export function filterRows<T extends InfraplanParsedRow>(rows: T[], filter: RowFilter): T[] {
    const needle = filter.search.trim().toLowerCase();
    return rows.filter(
        (r) =>
            (filter.section === "ALL" || r.section === filter.section) &&
            (!filter.onlyUnassigned || !isAssigned(r)) &&
            (!needle ||
                [r.primary_number, r.bezeichnung, r.massnahme, r.laender, ...(r.project_numbers ?? [])]
                    .filter(Boolean)
                    .some((v) => String(v).toLowerCase().includes(needle)) ||
                String(r.lfd_nr) === needle),
    );
}

// ---------------------------------------------------------------------------
// Project detail: deltas between years
// ---------------------------------------------------------------------------

type DeltaEntry = Pick<
    InfraplanProjectEntry,
    | "id"
    | "report_year"
    | "section"
    | "lfd_nr"
    | "primary_number"
    | "massnahme"
    | "bezeichnung"
    | "cost_mio"
    | "resolved_cost_mio"
    | "cost_kind"
    | "ibn_year"
    | "ibn_raw"
>;

/** A measure is the same across years when its primary project number is;
 *  without a number the measure name is the next best identity. */
export function measureKey(entry: Pick<DeltaEntry, "primary_number" | "massnahme" | "bezeichnung" | "section" | "lfd_nr">): string {
    if (entry.primary_number) return `nr:${entry.primary_number}`;
    const name = (entry.massnahme ?? entry.bezeichnung ?? "").trim().toLowerCase();
    return name ? `name:${name}` : `row:${entry.section}-${entry.lfd_nr}`;
}

export function entryCost(entry: Pick<DeltaEntry, "cost_mio" | "resolved_cost_mio">): number | null {
    return entry.cost_mio ?? entry.resolved_cost_mio ?? null;
}

/**
 * Change hints per entry id compared with the same measure in the previous
 * year that has it: "GWU +12 %", "IBN 2028 → 2030". The oldest year of a
 * measure gets no hints.
 */
export function entryDeltas(entries: DeltaEntry[]): Map<number, string[]> {
    const groups = new Map<string, DeltaEntry[]>();
    for (const e of entries) {
        const key = measureKey(e);
        groups.set(key, [...(groups.get(key) ?? []), e]);
    }
    const out = new Map<number, string[]>();
    for (const group of groups.values()) {
        const sorted = [...group].sort((a, b) => a.report_year - b.report_year);
        for (let i = 1; i < sorted.length; i++) {
            const prev = sorted[i - 1];
            const cur = sorted[i];
            if (prev.report_year === cur.report_year) continue;
            const hints: string[] = [];
            const before = entryCost(prev);
            const after = entryCost(cur);
            if (before !== null && after !== null && before !== after) {
                const pct = formatPercentChange(before, after);
                const label = cur.cost_kind === "GESAMTKOSTEN" ? "Kosten" : "GWU";
                if (pct) hints.push(`${label} ${pct}`);
            }
            if (prev.ibn_year != null && cur.ibn_year != null && prev.ibn_year !== cur.ibn_year) {
                hints.push(`IBN ${prev.ibn_year} → ${cur.ibn_year}`);
            } else if (prev.ibn_year != null && cur.ibn_year == null && cur.ibn_raw) {
                hints.push(`IBN ${prev.ibn_year} → ${cur.ibn_raw}`);
            }
            if (hints.length > 0) out.set(cur.id, hints);
        }
    }
    return out;
}

// ---------------------------------------------------------------------------
// Public page: KPI chart rows
// ---------------------------------------------------------------------------

export type KpiChartSeries = {
    name: string;
    label: string;
    color: string;
    type: "bar" | "line";
    strokeDasharray?: string;
};

export type KpiChart = {
    /** One row per value year: { year, [seriesName]: value }. */
    data: Record<string, number | string | null>[];
    series: KpiChartSeries[];
    /** The report year the Ist values are taken from. */
    istReportYear: number | null;
};

// Same Mantine palette tokens the other charts use (FinVe/GVFG): blue/teal
// for actual values, warm tones for targets.
const IST_COLORS = ["blue.6", "teal.6", "indigo.5", "cyan.6", "violet.5", "green.6"];
const ZIEL_COLORS = ["orange.6", "red.6", "grape.6", "yellow.7", "pink.6"];

function seriesSuffix(series: string | null | undefined): string {
    return series ? ` – ${series}` : "";
}

/** Distinct named sub-series of a KPI (e.g. the KMM categories), in order of appearance. */
export function kpiSubSeries(kpi: Pick<InfraplanPublicKpi, "values">): string[] {
    return [...new Set((kpi.values ?? []).map((v) => v.series).filter((s): s is string => !!s))];
}

/**
 * KPIs whose sub-series are not additive: one of them already is the whole
 * (the others are subsets of it), so the overview shows that one instead of
 * a sum. Keyed by KPI key.
 */
export const KPI_TOTAL_SERIES: Record<string, string> = {
    etcs_strecken_km: "Gesamtnetz",
};

export type KpiOverview = {
    /** What the overview chart shows. */
    scope: KpiChartScope;
    /** Sub-series that get their own chart in the detail view. */
    detailSeries: string[];
    /** Short hint under the KPI name; null when nothing is collapsed. */
    note: string | null;
};

/**
 * With several sub-series the overview shows one line of numbers per year —
 * the series that is the whole (KPI_TOTAL_SERIES) or else their sum — and the
 * split goes to a detail view, one chart per remaining sub-series.
 */
export function kpiOverview(kpi: Pick<InfraplanPublicKpi, "key" | "values">): KpiOverview {
    const sub = kpiSubSeries(kpi);
    if (sub.length < 2) return { scope: "all", detailSeries: [], note: null };
    const total = KPI_TOTAL_SERIES[kpi.key];
    if (total && sub.includes(total)) {
        return { scope: { series: total }, detailSeries: sub.filter((s) => s !== total), note: total };
    }
    return { scope: "total", detailSeries: sub, note: `Summe aus ${sub.length} Kategorien` };
}

/**
 * Which values a chart shows: all sub-series side by side (default), their sum
 * per year (`"total"`) or a single sub-series by name.
 */
export type KpiChartScope = "all" | "total" | { series: string };

/**
 * Ist values of the newest report year become (stacked) bars, one bar series
 * per sub-series; the targets of every report year become their own line
 * ("Ziel IP 2026"), so shifted targets stay visible.
 */
export function buildKpiChart(kpi: Pick<InfraplanPublicKpi, "values">, scope: KpiChartScope = "all"): KpiChart {
    let values = kpi.values ?? [];
    if (scope === "total") {
        // Collapse the sub-series; values of the same key are summed below.
        values = values.map((v) => ({ ...v, series: null }));
    } else if (scope !== "all") {
        values = values.filter((v) => v.series === scope.series).map((v) => ({ ...v, series: null }));
    }
    const istYears = values.filter((v) => v.value_kind === "IST").map((v) => v.report_year);
    const istReportYear = istYears.length > 0 ? Math.max(...istYears) : null;

    const rows = new Map<number, Record<string, number | string | null>>();
    const seriesMap = new Map<string, KpiChartSeries>();
    let istIdx = 0;
    const zielIdx = new Map<number, number>();
    const zielYears = [...new Set(values.filter((v) => v.value_kind === "ZIEL").map((v) => v.report_year))].sort(
        (a, b) => b - a,
    );
    zielYears.forEach((y, i) => zielIdx.set(y, i));

    for (const v of values) {
        let name: string;
        if (v.value_kind === "IST") {
            if (v.report_year !== istReportYear) continue;
            name = `ist|${v.series ?? ""}`;
            if (!seriesMap.has(name)) {
                seriesMap.set(name, {
                    name,
                    label: `Ist${seriesSuffix(v.series)}`,
                    color: IST_COLORS[istIdx++ % IST_COLORS.length],
                    type: "bar",
                });
            }
        } else {
            name = `ziel|${v.report_year}|${v.series ?? ""}`;
            if (!seriesMap.has(name)) {
                const i = zielIdx.get(v.report_year) ?? 0;
                seriesMap.set(name, {
                    name,
                    label: `Ziel IP ${v.report_year}${seriesSuffix(v.series)}`,
                    color: ZIEL_COLORS[i % ZIEL_COLORS.length],
                    type: "line",
                    // Older targets dashed, the newest solid.
                    strokeDasharray: i === 0 ? undefined : "5 4",
                });
            }
        }
        const row = rows.get(v.year) ?? { year: String(v.year) };
        const prev = row[name];
        row[name] = typeof prev === "number" ? prev + v.value : v.value;
        rows.set(v.year, row);
    }

    const data = [...rows.entries()].sort(([a], [b]) => a - b).map(([, row]) => row);
    // Bars first (drawn underneath), then lines from newest to oldest target.
    const series = [...seriesMap.values()].sort((a, b) => {
        if (a.type !== b.type) return a.type === "bar" ? -1 : 1;
        // Bars keep their order of appearance (stack order); lines newest first.
        return a.type === "bar" ? 0 : b.label.localeCompare(a.label, "de");
    });
    return { data, series, istReportYear };
}

/** KPIs grouped by kind, then category, each list in sort order. */
export function groupKpis<T extends Pick<InfraplanPublicKpi, "kind" | "category" | "sort_order" | "name">>(
    kpis: T[],
): { kind: string; categories: { category: string | null; kpis: T[] }[] }[] {
    const kindOrder = ["STEUERUNG", "INFORMATION"];
    const byKind = new Map<string, Map<string | null, T[]>>();
    for (const k of kpis) {
        const cats = byKind.get(k.kind) ?? new Map<string | null, T[]>();
        cats.set(k.category ?? null, [...(cats.get(k.category ?? null) ?? []), k]);
        byKind.set(k.kind, cats);
    }
    const rank = (kind: string) => {
        const i = kindOrder.indexOf(kind);
        return i === -1 ? kindOrder.length : i;
    };
    return [...byKind.entries()]
        .sort(([a], [b]) => rank(a) - rank(b) || a.localeCompare(b))
        .map(([kind, cats]) => ({
            kind,
            categories: [...cats.entries()]
                .sort(([a], [b]) => (a ?? "~").localeCompare(b ?? "~"))
                .map(([category, list]) => ({
                    category,
                    kpis: [...list].sort((x, y) => x.sort_order - y.sort_order || x.name.localeCompare(y.name, "de")),
                })),
        }));
}
