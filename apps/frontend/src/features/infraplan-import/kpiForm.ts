/**
 * Form state of the manual KPI entry (InfraplanKpiPage) and the diff that
 * turns it into a PUT payload. Only changed slots are sent: a manual write
 * stores the value as checked, so re-sending untouched AI values would
 * approve them silently.
 */

import type { InfraplanKpiValue, InfraplanKpiValueInput } from "../../shared/api/queries";

export type KpiFormRow = {
    /** Client-side id for React keys. */
    uid: string;
    kpi_key: string;
    year: number | null;
    value_kind: "IST" | "ZIEL";
    series: string;
    value: number | null;
    source_page: number | null;
};

let counter = 0;
export function newUid(): string {
    counter += 1;
    return `row-${counter}`;
}

export function toFormRows(values: InfraplanKpiValue[]): KpiFormRow[] {
    return values.map((v) => ({
        uid: newUid(),
        kpi_key: v.kpi_key,
        year: v.year,
        value_kind: v.value_kind,
        series: v.series ?? "",
        value: v.value,
        source_page: v.source_page ?? null,
    }));
}

/** The identity of a stored value: one per KPI × year × Ist/Ziel × series. */
export function slotKey(v: { kpi_key: string; year: number | null; value_kind: string; series?: string | null }): string {
    return `${v.kpi_key}|${v.year}|${v.value_kind}|${(v.series ?? "").trim()}`;
}

/** Rows that cannot be saved: missing year or value, or a duplicate slot. */
export function invalidRows(rows: KpiFormRow[]): Set<string> {
    const bad = new Set<string>();
    const seen = new Map<string, string>();
    for (const r of rows) {
        if (r.year === null || r.value === null) {
            bad.add(r.uid);
            continue;
        }
        const key = slotKey(r);
        const other = seen.get(key);
        if (other) {
            bad.add(r.uid);
            bad.add(other);
        } else {
            seen.set(key, r.uid);
        }
    }
    return bad;
}

/**
 * PUT payload for one KPI: new or changed slots with their value, slots that
 * disappeared (deleted row, or its year/kind/series edited) with ``null``.
 */
export function buildKpiPayload(original: InfraplanKpiValue[], rows: KpiFormRow[]): InfraplanKpiValueInput[] {
    const before = new Map(original.map((v) => [slotKey(v), v]));
    const out: InfraplanKpiValueInput[] = [];
    const kept = new Set<string>();
    for (const r of rows) {
        if (r.year === null || r.value === null) continue;
        const key = slotKey(r);
        kept.add(key);
        const old = before.get(key);
        if (old && old.value === r.value && (old.source_page ?? null) === r.source_page) continue;
        out.push({
            kpi_key: r.kpi_key,
            year: r.year,
            value_kind: r.value_kind,
            series: r.series.trim() || null,
            value: r.value,
            source_page: r.source_page,
        });
    }
    for (const [key, old] of before) {
        if (kept.has(key)) continue;
        out.push({
            kpi_key: old.kpi_key,
            year: old.year,
            value_kind: old.value_kind,
            series: old.series ?? null,
            value: null,
        });
    }
    return out;
}
