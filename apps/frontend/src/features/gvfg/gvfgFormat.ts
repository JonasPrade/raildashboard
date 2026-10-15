import type { GvfgEntry, GvfgProgram } from "../../shared/api/queries";

type Amount = GvfgEntry["amounts"][number];

export const CATEGORY_LABEL: Record<string, string> = { SUM: "∑", A: "Kat. A", B: "Kat. B", C: "Kat. C" };
export const KIND_LABEL: Record<string, string> = { kommunal: "kommunal", db: "DB" };

/** Decimal strings from the API → number (null stays null). */
export function num(value: string | number | null | undefined): number | null {
    if (value === null || value === undefined || value === "") return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
}

/** "1.234,56" — amounts are in Mio. €. */
export function formatMio(value: string | number | null | undefined): string {
    const n = num(value);
    return n === null ? "–" : n.toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function sumLine(entry: Pick<GvfgEntry, "amounts">): Amount | undefined {
    return entry.amounts.find((a) => a.category === "SUM");
}

/** Categories printed for an entry, e.g. "A, C". */
export function categories(entry: Pick<GvfgEntry, "amounts">): string {
    const cats = entry.amounts
        .filter((a) => a.category !== "SUM" && (num(a.aid_total) ?? 0) !== 0)
        .map((a) => a.category);
    return [...new Set(cats)].join(", ") || "–";
}

/** Aid planned within the edition's own years (the "geplant" columns). */
export function plannedAid(entry: Pick<GvfgEntry, "amounts">, program: GvfgProgram): number | null {
    const line = sumLine(entry);
    if (!line) return null;
    const labels = program.periods.filter((p) => p.kind === "geplant").map((p) => p.label);
    if (labels.length === 0) return null;
    return labels.reduce((acc, label) => acc + (num(line.periods[label]) ?? 0), 0);
}

export function editionLabel(program: Pick<GvfgProgram, "year_from" | "year_to">): string {
    return `${program.year_from}–${program.year_to}`;
}
