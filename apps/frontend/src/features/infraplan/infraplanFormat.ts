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
    /** "right" for the companion KPI on its own scale. */
    yAxisId?: "left" | "right";
    /** Unit shown in the tooltip, e.g. "km". */
    unit?: string;
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
const COMPANION_IST_COLOR = "gray.5";
const COMPANION_ZIEL_COLORS = ["yellow.6", "lime.7"];

/**
 * A second statement drawn into a KPI's chart on its own right-hand scale,
 * e.g. the ETCS equipment rate (%) next to the ETCS route km. Set per KPI in
 * the admin settings (``companion_key``); the companion KPI has the same
 * sub-series and gets no card of its own.
 */
export type KpiCompanion = { kpi: Pick<InfraplanPublicKpi, "values">; label: string; unit: string };

type KpiSettings = Pick<InfraplanPublicKpi, "key" | "name" | "unit" | "values" | "companion_key" | "companion_label">;

/** Keys of the KPIs drawn inside another KPI's chart. */
export function companionKeys(kpis: Pick<InfraplanPublicKpi, "companion_key">[]): Set<string> {
    return new Set(kpis.map((k) => k.companion_key).filter((k): k is string => !!k));
}

/** Companion of each KPI that has one with values, keyed by the main KPI. */
export function kpiCompanions(kpis: KpiSettings[]): Map<string, KpiCompanion> {
    const byKey = new Map(kpis.map((k) => [k.key, k]));
    const out = new Map<string, KpiCompanion>();
    for (const k of kpis) {
        const c = k.companion_key ? byKey.get(k.companion_key) : undefined;
        if (c && (c.values ?? []).length > 0) {
            out.set(k.key, { kpi: c, label: k.companion_label || c.name, unit: c.unit ?? "" });
        }
    }
    return out;
}

function seriesSuffix(series: string | null | undefined): string {
    return series ? ` – ${series}` : "";
}

/** Distinct named sub-series of a KPI (e.g. the KMM categories), in order of appearance. */
export function kpiSubSeries(kpi: Pick<InfraplanPublicKpi, "values">): string[] {
    return [...new Set((kpi.values ?? []).map((v) => v.series).filter((s): s is string => !!s))];
}

/**
 * ``chart_layout`` of a KPI (admin settings), where the generic rules do not fit:
 * - "split": the sub-series are separate statements (overlapping shares),
 *   one small chart each right in the card;
 * - "grouped": bars side by side, not stacked (a running stock next to its
 *   annual inflows and outflows is not additive);
 * - "flow": one year split into Herkunft/Einsatz (Mittelherkunft), shown as
 *   two ranked lists instead of a time chart.
 */
export type KpiOverview = {
    layout: "chart" | "split" | "flow";
    /** What the overview chart shows. */
    scope: KpiChartScope;
    /** Whether the Ist bars of several sub-series stack. */
    stacked: boolean;
    /** Sub-series that get their own chart (detail view, or inline for "split"). */
    detailSeries: string[];
    /** Short hint under the KPI name; null when nothing is collapsed. */
    note: string | null;
};

/**
 * With several sub-series the overview shows one line of numbers per year —
 * the series that is the whole (``total_series``) or else their sum — and the
 * split goes to a detail view, one chart per remaining sub-series. Ist-only
 * splits stay a stack; ``chart_layout`` overrides all of this.
 */
export function kpiOverview(
    kpi: Pick<InfraplanPublicKpi, "values" | "chart_layout" | "total_series">,
): KpiOverview {
    const sub = kpiSubSeries(kpi);
    const plain = { layout: "chart" as const, scope: "all" as const, stacked: true, detailSeries: [], note: null };
    const layout = kpi.chart_layout;
    if (layout === "flow") return { ...plain, layout: "flow" };
    if (sub.length < 2) return plain;
    if (layout === "split") return { ...plain, layout: "split", detailSeries: sub };
    if (layout === "grouped") return { ...plain, stacked: false };
    const total = kpi.total_series;
    if (total && sub.includes(total)) {
        return { ...plain, scope: { series: total }, detailSeries: sub.filter((s) => s !== total), note: total };
    }
    // Ist-only splits stay readable as a stack (the tooltip adds the sum);
    // it is one target line per sub-series that clutters the chart.
    if (!(kpi.values ?? []).some((v) => v.value_kind === "ZIEL" && v.series)) return plain;
    return { ...plain, scope: "total", detailSeries: sub, note: `Summe aus ${sub.length} Kategorien` };
}

export type KpiFlowItem = { label: string; value: number };
export type KpiFlow = { year: number; herkunft: KpiFlowItem[]; einsatz: KpiFlowItem[] };

/**
 * The newest Ist year of a Herkunft/Einsatz KPI, its series named
 * "Herkunft: …" and "Einsatz: …", each side sorted by size.
 */
export function kpiFlow(kpi: Pick<InfraplanPublicKpi, "values">): KpiFlow | null {
    const ist = (kpi.values ?? []).filter((v) => v.value_kind === "IST" && v.series);
    if (ist.length === 0) return null;
    const year = Math.max(...ist.map((v) => v.year));
    const reportYear = Math.max(...ist.filter((v) => v.year === year).map((v) => v.report_year));
    const side = (prefix: string) =>
        ist
            .filter((v) => v.year === year && v.report_year === reportYear && v.series!.startsWith(prefix))
            .map((v) => ({ label: v.series!.slice(prefix.length).trim(), value: v.value }))
            .sort((a, b) => b.value - a.value);
    return { year, herkunft: side("Herkunft:"), einsatz: side("Einsatz:") };
}

/**
 * Which values a chart shows: all sub-series side by side (default), their sum
 * per year (`"total"`) or a single sub-series by name.
 */
export type KpiChartScope = "all" | "total" | { series: string };

type KpiValue = NonNullable<InfraplanPublicKpi["values"]>[number];

function scopeValues(values: InfraplanPublicKpi["values"], scope: KpiChartScope): KpiValue[] {
    const all = values ?? [];
    // "total" collapses the sub-series; values of the same key are summed.
    if (scope === "total") return all.map((v) => ({ ...v, series: null }));
    if (scope === "all") return all;
    return all.filter((v) => v.series === scope.series).map((v) => ({ ...v, series: null }));
}

/**
 * Ist values of the newest report year become (stacked) bars, one bar series
 * per sub-series; the targets of every report year become their own line
 * ("Ziel IP 2026"), so shifted targets stay visible. A companion KPI is drawn
 * the same way on the right axis, its bars in a stack of their own so they
 * stand next to the main bars.
 */
export function buildKpiChart(
    kpi: Pick<InfraplanPublicKpi, "values"> & { unit?: string | null },
    scope: KpiChartScope = "all",
    companion?: { kpi: Pick<InfraplanPublicKpi, "values">; label: string; unit: string },
): KpiChart {
    const main = scopeValues(kpi.values, scope);
    const istYears = main.filter((v) => v.value_kind === "IST").map((v) => v.report_year);
    const istReportYear = istYears.length > 0 ? Math.max(...istYears) : null;

    const rows = new Map<number, Record<string, number | string | null>>();
    const seriesMap = new Map<string, KpiChartSeries>();

    const add = (
        values: KpiValue[],
        opts: { prefix: string; label: string; zielSuffix?: string; unit?: string; right: boolean },
    ) => {
        const ist = values.filter((v) => v.value_kind === "IST").map((v) => v.report_year);
        const istYear = ist.length > 0 ? Math.max(...ist) : null;
        const zielYears = [...new Set(values.filter((v) => v.value_kind === "ZIEL").map((v) => v.report_year))].sort(
            (a, b) => b - a,
        );
        let istIdx = 0;
        const axis = opts.right ? { yAxisId: "right" as const } : {};
        for (const v of values) {
            let name: string;
            if (v.value_kind === "IST") {
                if (v.report_year !== istYear) continue;
                name = `${opts.prefix}ist|${v.series ?? ""}`;
                if (!seriesMap.has(name)) {
                    seriesMap.set(name, {
                        name,
                        label: `${opts.label}${seriesSuffix(v.series)}`,
                        color: opts.right ? COMPANION_IST_COLOR : IST_COLORS[istIdx++ % IST_COLORS.length],
                        type: "bar",
                        unit: opts.unit,
                        ...axis,
                    });
                }
            } else {
                name = `${opts.prefix}ziel|${v.report_year}|${v.series ?? ""}`;
                if (!seriesMap.has(name)) {
                    const i = Math.max(zielYears.indexOf(v.report_year), 0);
                    const colors = opts.right ? COMPANION_ZIEL_COLORS : ZIEL_COLORS;
                    seriesMap.set(name, {
                        name,
                        label: `Ziel${opts.right ? ` ${opts.label}` : (opts.zielSuffix ?? "")} IP ${v.report_year}${seriesSuffix(v.series)}`,
                        color: colors[i % colors.length],
                        type: "line",
                        // Older targets dashed, the newest solid.
                        strokeDasharray: i === 0 ? undefined : "5 4",
                        unit: opts.unit,
                        ...axis,
                    });
                }
            }
            const row = rows.get(v.year) ?? { year: String(v.year) };
            const prev = row[name];
            row[name] = typeof prev === "number" ? prev + v.value : v.value;
            rows.set(v.year, row);
        }
    };

    // With two scales the legend names the unit, so each bar maps to its axis.
    const mainLabel = companion && kpi.unit ? `Ist (${kpi.unit})` : "Ist";
    const zielSuffix = companion && kpi.unit ? ` (${kpi.unit})` : "";
    add(main, { prefix: "", label: mainLabel, zielSuffix, unit: kpi.unit ?? undefined, right: false });
    if (companion) {
        add(scopeValues(companion.kpi.values, scope), {
            prefix: "r:",
            label: `${companion.label} (${companion.unit})`,
            unit: companion.unit,
            right: true,
        });
    }

    // Without any target the "Ist – " prefix says nothing; name the sub-series only.
    if (![...seriesMap.values()].some((x) => x.type === "line")) {
        for (const x of seriesMap.values()) {
            if (!x.yAxisId && x.label.startsWith("Ist – ")) x.label = x.label.slice("Ist – ".length);
        }
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

/**
 * Axis for a KPI with ``zoomed_axis`` (values in a narrow band far from zero,
 * a rate close to 100 %): whole numbers around the main-axis values, with
 * headroom below. The page says under the chart where the axis starts.
 */
export function zoomedDomain(chart: Pick<KpiChart, "data" | "series">, unit?: string | null): [number, number] | null {
    const keys = chart.series.filter((s) => s.yAxisId !== "right").map((s) => s.name);
    const values = chart.data.flatMap((row) =>
        keys.map((k) => row[k]).filter((v): v is number => typeof v === "number"),
    );
    if (values.length === 0) return null;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    const hi = Math.ceil(max + span / 4);
    // A rate never exceeds 100 %.
    return [Math.floor(min - span), unit === "%" ? Math.min(hi, Math.max(100, Math.ceil(max))) : hi];
}

/** Name of the synthetic tooltip row that carries the stack total. */
export const STACK_TOTAL_KEY = "__summe";

/**
 * Sum of the stacked main-axis bars in a tooltip payload; null when fewer
 * than two of them have a value (a single bar is its own total).
 */
export function stackTotal(
    payload: readonly { name?: string | number; value?: unknown }[],
    series: Pick<KpiChartSeries, "name" | "type" | "yAxisId">[],
): number | null {
    const stacked = new Set(series.filter((s) => s.type === "bar" && s.yAxisId !== "right").map((s) => s.name));
    const values = payload
        .filter((p) => stacked.has(String(p.name)) && typeof p.value === "number")
        .map((p) => p.value as number);
    return values.length < 2 ? null : values.reduce((a, b) => a + b, 0);
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
