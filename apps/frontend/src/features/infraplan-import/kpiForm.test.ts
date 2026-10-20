import { describe, expect, it } from "vitest";

import type { InfraplanKpiValue } from "../../shared/api/queries";
import { buildKpiPayload, invalidRows, toFormRows, type KpiFormRow } from "./kpiForm";

const stored: InfraplanKpiValue[] = [
    {
        id: 1,
        kpi_key: "gleis_km",
        report_year: 2026,
        year: 2024,
        value_kind: "IST",
        series: null,
        value: 40,
        source_page: 12,
        status: "UNGEPRUEFT",
    },
    {
        id: 2,
        kpi_key: "gleis_km",
        report_year: 2026,
        year: 2025,
        value_kind: "IST",
        series: null,
        value: 50,
        source_page: 12,
        status: "UNGEPRUEFT",
    },
];

describe("buildKpiPayload", () => {
    it("sends nothing while the form is untouched (no silent approval)", () => {
        expect(buildKpiPayload(stored, toFormRows(stored))).toEqual([]);
    });

    it("sends changed and new slots and removes deleted ones", () => {
        const rows = toFormRows(stored);
        const edited: KpiFormRow[] = [
            { ...rows[0], value: 42 },
            // rows[1] deleted
            { ...rows[0], uid: "new", year: 2026, value_kind: "ZIEL", value: 60, source_page: null },
        ];
        expect(buildKpiPayload(stored, edited)).toEqual([
            { kpi_key: "gleis_km", year: 2024, value_kind: "IST", series: null, value: 42, source_page: 12 },
            { kpi_key: "gleis_km", year: 2026, value_kind: "ZIEL", series: null, value: 60, source_page: null },
            { kpi_key: "gleis_km", year: 2025, value_kind: "IST", series: null, value: null },
        ]);
    });

    it("moves a value when its series changes", () => {
        const rows = toFormRows(stored.slice(0, 1));
        const payload = buildKpiPayload(stored.slice(0, 1), [{ ...rows[0], series: " Teil 1 " }]);
        expect(payload).toEqual([
            { kpi_key: "gleis_km", year: 2024, value_kind: "IST", series: "Teil 1", value: 40, source_page: 12 },
            { kpi_key: "gleis_km", year: 2024, value_kind: "IST", series: null, value: null },
        ]);
    });
});

describe("invalidRows", () => {
    it("flags missing values and duplicate slots", () => {
        const rows = toFormRows(stored);
        const bad = invalidRows([rows[0], { ...rows[1], year: 2024 }, { ...rows[1], uid: "x", value: null }]);
        expect(bad).toEqual(new Set([rows[0].uid, rows[1].uid, "x"]));
    });
});
