import { describe, expect, it } from "vitest";
import type { ConditionAssetClass, ConditionSeriesValue, ConditionValue } from "../../shared/api/queries";
import { ValueIndex, classRows, formatDelta, headlines, landRows, landStep, trend } from "./conditionFormat";

let id = 0;
const v = (p: Partial<ConditionValue> & Pick<ConditionValue, "metric" | "value">): ConditionValue => ({
    id: ++id,
    domain: "FAHRWEG",
    scope: "GESAMT",
    region: null,
    class_key: null,
    grade: null,
    reference_year: 2025,
    source_page: null,
    source_ref: null,
    status: "GEPRUEFT",
    ...p,
});
const cls = (key: string, name: string, domain: "FAHRWEG" | "PERSONENBAHNHOF" = "FAHRWEG"): ConditionAssetClass => ({
    key,
    name,
    domain,
    trade: null,
    unit: "Stk.",
    sort_order: 0,
});

const values: ConditionValue[] = [
    v({ metric: "NOTE", value: 3.0 }),
    v({ metric: "NOTE", value: 3.0, reference_year: 2024 }),
    v({ metric: "ERNEUERUNGSBEDARF_MRD", value: 105.9 }),
    v({ metric: "ERNEUERUNGSBEDARF_MRD", value: 109.8, reference_year: 2024 }),
    v({ metric: "NOTE", value: 3.04, scope: "HLN" }),
    v({ class_key: "fw_stellwerke", metric: "NOTE", value: 4.02 }),
    v({ class_key: "fw_stellwerke", metric: "WBW_BEWERTET", value: 63.5 }),
    ...[0.9, 8.6, 32.8, 42.3, 14.4, 0.9].map((p, i) =>
        v({ class_key: "fw_stellwerke", metric: "VERTEILUNG_WBW", grade: i + 1, value: p }),
    ),
    v({ class_key: "fw_stellwerke", metric: "ERNEUERUNGSBEDARF_MENGE", value: 2026 }),
    v({ class_key: "fw_bruecken", metric: "NOTE", value: 2.64 }),
    v({ class_key: "fw_bruecken", metric: "WBW_BEWERTET", value: 336.6 }),
    // A class with a grade but no WBW is not part of the table.
    v({ class_key: "fw_tunnel", metric: "NOTE", value: 2.17 }),
    v({ scope: "LAND", region: "TH", metric: "NOTE", value: 2.65 }),
    v({ scope: "LAND", region: "NW", metric: "NOTE", value: 3.26 }),
];
const classes = [cls("fw_bruecken", "Brücken"), cls("fw_tunnel", "Tunnel"), cls("fw_stellwerke", "Stellwerke")];

describe("conditionFormat", () => {
    const index = new ValueIndex(values);

    it("reads headline figures with the previous year", () => {
        const [note, need, hln, fln] = headlines(index, "FAHRWEG", 2025);
        expect(note).toMatchObject({ value: 3, previous: 3 });
        expect(need).toMatchObject({ value: 105.9, previous: 109.8, unit: "Mrd. €" });
        expect(hln.value).toBe(3.04);
        expect(fln.value).toBeNull();
    });

    it("builds class rows sorted by grade, worst first, with the distribution", () => {
        const series: ConditionSeriesValue[] = [
            { ...v({ class_key: "fw_stellwerke", metric: "NOTE", value: 4.12, reference_year: 2024 }), report_year: 2024 },
        ];
        const rows = classRows(index, classes, "FAHRWEG", "GESAMT", 2025, series);
        expect(rows.map((r) => r.key)).toEqual(["fw_stellwerke", "fw_bruecken"]);
        expect(rows[0]).toMatchObject({ need: 2026, previousNote: 4.12, wbw: 63.5 });
        expect(rows[0].distribution).toEqual([0.9, 8.6, 32.8, 42.3, 14.4, 0.9]);
        expect(rows[1].distribution).toBeNull();
        expect(classRows(index, classes, "FAHRWEG", "GESAMT", 2025, [], "wbw")[0].key).toBe("fw_bruecken");
    });

    it("ranks the Länder, best first, and steps them against the average", () => {
        expect(landRows(index, "FAHRWEG", 2025).map((r) => r.code)).toEqual(["TH", "NW"]);
        expect(landStep(2.65, 3.0)).toBe(1);
        expect(landStep(2.95, 3.0)).toBe(2);
        expect(landStep(3.02, 3.0)).toBe(3);
        expect(landStep(3.1, 3.0)).toBe(4);
        expect(landStep(3.26, 3.0)).toBe(5);
    });

    it("draws the trend up to the chosen year only", () => {
        const series: ConditionSeriesValue[] = [2023, 2024, 2025, 2026].map((y) => ({
            ...v({ metric: "NOTE", value: 3, reference_year: y }),
            report_year: y,
        }));
        expect(trend(series, 2025).map((p) => p.year)).toEqual([2023, 2024, 2025]);
    });

    it("formats grade changes with sign", () => {
        expect(formatDelta(-0.07)).toBe("−0,07");
        expect(formatDelta(0.1)).toBe("+0,10");
        expect(formatDelta(0.001)).toBe("± 0,00");
    });
});
