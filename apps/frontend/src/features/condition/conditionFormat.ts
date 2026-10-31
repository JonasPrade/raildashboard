// Shaping of the InfraGO-Zustandsbericht values for /netzzustand
// (docs/features/feature-zustandsbericht.md → "Darstellung").
import type { ConditionAssetClass, ConditionSeriesValue, ConditionValue } from "../../shared/api/queries";

export type Domain = "FAHRWEG" | "PERSONENBAHNHOF";
export type Scope = "GESAMT" | "HLN" | "FLN" | "SE";

export const GRADES = [1, 2, 3, 4, 5, 6] as const;
export const GRADE_LABEL: Record<number, string> = {
    1: "Neuwertig",
    2: "Gut",
    3: "Mittelmäßig",
    4: "Schlecht",
    5: "Mangelhaft",
    6: "Einschränkend",
};

export const SCOPE_LABEL: Record<Scope, string> = {
    GESAMT: "Gesamtnetz",
    HLN: "Hochleistungsnetz",
    FLN: "Flächennetz",
    SE: "Serviceeinrichtungen",
};
export const SCOPE_SHORT: Record<Scope, string> = { GESAMT: "Gesamtnetz", HLN: "HLN", FLN: "FLN", SE: "SE" };

export const TRADE_LABEL: Record<string, string> = {
    KIB: "Ingenieurbauwerke",
    OB: "Oberbau",
    LST: "Leit- und Sicherungstechnik",
    ET: "Elektrotechnik",
};

export const LAENDER: Record<string, string> = {
    BW: "Baden-Württemberg",
    BY: "Bayern",
    BE: "Berlin",
    BB: "Brandenburg",
    HB: "Bremen",
    HH: "Hamburg",
    HE: "Hessen",
    MV: "Mecklenburg-Vorpommern",
    NI: "Niedersachsen",
    NW: "Nordrhein-Westfalen",
    RP: "Rheinland-Pfalz",
    SL: "Saarland",
    SN: "Sachsen",
    ST: "Sachsen-Anhalt",
    SH: "Schleswig-Holstein",
    TH: "Thüringen",
};

/** Tile map: [row, column] of each Land in a 7 × 6 grid, roughly where it lies. */
export const LAND_TILE: Record<string, [number, number]> = {
    SH: [0, 2], HH: [1, 2], MV: [1, 3], HB: [2, 1], NI: [2, 2], BE: [2, 4],
    NW: [3, 1], ST: [3, 3], BB: [3, 4], HE: [4, 2], TH: [4, 3], SN: [4, 4],
    RP: [5, 1], BW: [5, 2], BY: [5, 3], SL: [6, 1],
};

const de = (digits: number) => (v: number) =>
    v.toLocaleString("de-DE", { minimumFractionDigits: digits, maximumFractionDigits: digits });
export const formatNote = de(2);
export const formatMrd = de(1);
export const formatPct = de(1);
export const formatInt = (v: number) => v.toLocaleString("de-DE", { maximumFractionDigits: 0 });

/** "−0,07", "+0,10", "± 0,00" — the change of a grade (lower is better). */
export function formatDelta(v: number, digits = 2): string {
    const rounded = Number(v.toFixed(digits));
    if (rounded === 0) return `± ${de(digits)(0)}`;
    return `${rounded > 0 ? "+" : "−"}${de(digits)(Math.abs(rounded))}`;
}

type Slot = {
    domain: Domain;
    scope: Scope | "LAND";
    region?: string | null;
    classKey?: string | null;
    metric: string;
    grade?: number | null;
    year: number;
};

/** Lookup of the values of one year by their slot. */
export class ValueIndex {
    private readonly byKey = new Map<string, number>();

    constructor(values: ConditionValue[]) {
        for (const v of values) {
            this.byKey.set(
                ValueIndex.key({
                    domain: v.domain,
                    scope: v.scope,
                    region: v.region,
                    classKey: v.class_key,
                    metric: v.metric,
                    grade: v.grade,
                    year: v.reference_year,
                }),
                v.value,
            );
        }
    }

    static key(s: Slot): string {
        return [s.domain, s.scope, s.region ?? "", s.classKey ?? "", s.metric, s.grade ?? "", s.year].join("|");
    }

    get(slot: Slot): number | null {
        return this.byKey.get(ValueIndex.key(slot)) ?? null;
    }

    /** Distribution over grades 1–6 in %, or null when the report has none. */
    distribution(slot: Omit<Slot, "metric" | "grade">, metric = "VERTEILUNG_WBW"): number[] | null {
        const values = GRADES.map((grade) => this.get({ ...slot, metric, grade }));
        return values.every((v) => v === null) ? null : values.map((v) => v ?? 0);
    }

    hasScope(domain: Domain, scope: Scope, year: number): boolean {
        return this.get({ domain, scope, metric: "NOTE", year }) !== null;
    }
}

export type ClassRow = {
    key: string;
    name: string;
    trade: string | null;
    unit: string | null;
    note: number;
    wbw: number | null;
    distribution: number[] | null;
    counts: number[] | null;
    rated: number | null;
    stock: number | null;
    /** Fahrweg: quantity with grade 4–6; Personenbahnhöfe: Mrd. €. */
    need: number | null;
    previousNote: number | null;
};

export type SortKey = "note" | "wbw" | "name";

export function classRows(
    index: ValueIndex,
    classes: ConditionAssetClass[],
    domain: Domain,
    scope: Scope,
    year: number,
    series: ConditionSeriesValue[] = [],
    sort: SortKey = "note",
): ClassRow[] {
    const previous = new Map<string, number>();
    for (const v of series) {
        if (v.domain === domain && v.scope === scope && v.metric === "NOTE" && v.class_key && v.reference_year === year - 1) {
            previous.set(v.class_key, v.value);
        }
    }
    const rows: ClassRow[] = [];
    for (const c of classes) {
        if (c.domain !== domain) continue;
        const slot = { domain, scope, classKey: c.key, year };
        const note = index.get({ ...slot, metric: "NOTE" });
        // Without a grade the class is not part of this table (Empfangsgebäude, SE classes).
        if (note === null || index.get({ ...slot, metric: "WBW_BEWERTET" }) === null) continue;
        rows.push({
            key: c.key,
            name: c.name,
            trade: c.trade ?? null,
            unit: c.unit ?? null,
            note,
            wbw: index.get({ ...slot, metric: "WBW_BEWERTET" }),
            distribution: index.distribution(slot),
            counts: index.distribution(slot, "VERTEILUNG_MENGE"),
            rated: index.get({ ...slot, metric: "MENGE_BEWERTET" }),
            stock: index.get({ ...slot, metric: "MENGE_GESAMT" }),
            need:
                domain === "FAHRWEG"
                    ? index.get({ ...slot, metric: "ERNEUERUNGSBEDARF_MENGE" })
                    : index.get({ ...slot, metric: "NACHHOLBEDARF_MRD" }),
            previousNote: previous.get(c.key) ?? null,
        });
    }
    const by: Record<SortKey, (a: ClassRow, b: ClassRow) => number> = {
        note: (a, b) => b.note - a.note,
        wbw: (a, b) => (b.wbw ?? 0) - (a.wbw ?? 0),
        name: (a, b) => a.name.localeCompare(b.name, "de"),
    };
    return rows.sort(by[sort]);
}

export type Headline = { label: string; value: number | null; unit?: string; previous: number | null; digits: number; note?: string };

/** The four figures of the band, with the previous year where the report gives it. */
export function headlines(index: ValueIndex, domain: Domain, year: number): Headline[] {
    const total = (scope: Scope, metric: string, y = year) => index.get({ domain, scope, metric, year: y });
    if (domain === "FAHRWEG") {
        return [
            { label: "Netzzustandsnote", value: total("GESAMT", "NOTE"), previous: total("GESAMT", "NOTE", year - 1), digits: 2 },
            {
                label: "Zustandsbasierter Erneuerungsbedarf",
                value: total("GESAMT", "ERNEUERUNGSBEDARF_MRD"),
                unit: "Mrd. €",
                previous: total("GESAMT", "ERNEUERUNGSBEDARF_MRD", year - 1),
                digits: 1,
            },
            { label: "Zustandsnote Hochleistungsnetz", value: total("HLN", "NOTE"), previous: total("HLN", "NOTE", year - 1), digits: 2 },
            {
                label: "Zustandsnote Flächennetz",
                value: total("FLN", "NOTE"),
                previous: total("FLN", "NOTE", year - 1),
                digits: 2,
                note: index.hasScope("FAHRWEG", "SE", year) ? "inkl. Serviceeinrichtungen" : undefined,
            },
        ];
    }
    const station = (metric: string, y = year, classKey: string | null = null) =>
        index.get({ domain, scope: "GESAMT", classKey, metric, year: y });
    return [
        { label: "Zustandsnote Personenbahnhöfe", value: station("NOTE"), previous: station("NOTE", year - 1), digits: 2 },
        {
            label: "Zustandsbasierter Nachholbedarf",
            value: station("NACHHOLBEDARF_MRD"),
            unit: "Mrd. €",
            previous: station("NACHHOLBEDARF_MRD", year - 1),
            digits: 1,
        },
        {
            label: "Zustandsnote Empfangsgebäude",
            value: station("NOTE", year, "pb_empfangsgebaeude"),
            previous: station("NOTE", year - 1, "pb_empfangsgebaeude"),
            digits: 2,
        },
        {
            label: "Bewerteter Wiederbeschaffungswert",
            value: station("WBW_BEWERTET"),
            unit: "Mrd. €",
            previous: station("WBW_BEWERTET", year - 1),
            digits: 1,
        },
    ];
}

export type TrendPoint = { year: number; FAHRWEG?: number; PERSONENBAHNHOF?: number };

/** Netzzustandsnote and station grade over the years, up to ``untilYear``. */
export function trend(series: ConditionSeriesValue[], untilYear: number): TrendPoint[] {
    const points = new Map<number, TrendPoint>();
    for (const v of series) {
        if (v.metric !== "NOTE" || v.scope !== "GESAMT" || v.class_key || v.reference_year > untilYear) continue;
        const point = points.get(v.reference_year) ?? { year: v.reference_year };
        point[v.domain as Domain] = v.value;
        points.set(v.reference_year, point);
    }
    return [...points.values()].sort((a, b) => a.year - b.year);
}

export type LandRow = { code: string; name: string; note: number };

export function landRows(index: ValueIndex, domain: Domain, year: number): LandRow[] {
    return Object.entries(LAENDER)
        .map(([code, name]) => ({ code, name, note: index.get({ domain, scope: "LAND", region: code, metric: "NOTE", year }) }))
        .filter((r): r is LandRow => r.note !== null)
        .sort((a, b) => a.note - b.note);
}

/** Five steps of distance from the national grade: much better … much worse. */
export function landStep(note: number, average: number): 1 | 2 | 3 | 4 | 5 {
    const d = note - average;
    if (d <= -0.15) return 1;
    if (d < -0.03) return 2;
    if (d <= 0.03) return 3;
    if (d < 0.15) return 4;
    return 5;
}
