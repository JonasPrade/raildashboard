import { describe, expect, it } from "vitest";

import type { InfraplanParsedRow, InfraplanPublicKpi } from "../../shared/api/queries";
import {
    buildKpiChart,
    entryDeltas,
    filterRows,
    formatPercentChange,
    groupKpis,
    companionKeys,
    kpiCompanions,
    kpiFlow,
    kpiOverview,
    kpiSubSeries,
    measureKey,
    stackTotal,
    zoomedDomain,
} from "./infraplanFormat";

function entry(overrides: Partial<Parameters<typeof entryDeltas>[0][number]>) {
    return {
        id: 1,
        report_year: 2026,
        section: "BP_A",
        lfd_nr: 1,
        primary_number: "2-003-V01",
        massnahme: "ABS Hamburg–Berlin",
        bezeichnung: null,
        cost_mio: 100,
        resolved_cost_mio: null,
        cost_kind: "GWU",
        ibn_year: 2028,
        ibn_raw: "2028",
        ...overrides,
    };
}

describe("formatPercentChange", () => {
    it("uses a real minus sign and rounds", () => {
        expect(formatPercentChange(100, 112.4)).toBe("+12 %");
        expect(formatPercentChange(200, 194)).toBe("−3 %");
        expect(formatPercentChange(100, 100.2)).toBe("±0 %");
        expect(formatPercentChange(0, 5)).toBeNull();
    });
});

describe("entryDeltas", () => {
    it("compares a measure with its previous year by project number", () => {
        const deltas = entryDeltas([
            entry({ id: 1, report_year: 2026, lfd_nr: 4 }),
            entry({ id: 2, report_year: 2027, lfd_nr: 9, cost_mio: 112, ibn_year: 2030, ibn_raw: "2030" }),
        ]);
        expect(deltas.get(1)).toBeUndefined();
        expect(deltas.get(2)).toEqual(["GWU +12 %", "IBN 2028 → 2030"]);
    });

    it("uses the resolved cost of a reference and names Gesamtkosten", () => {
        const deltas = entryDeltas([
            entry({ id: 1, report_year: 2026, cost_kind: "GESAMTKOSTEN", cost_mio: null, resolved_cost_mio: 50 }),
            entry({ id: 2, report_year: 2027, cost_kind: "GESAMTKOSTEN", cost_mio: 40 }),
        ]);
        expect(deltas.get(2)).toEqual(["Kosten −20 %"]);
    });

    it("keeps different measures apart and skips unchanged ones", () => {
        const deltas = entryDeltas([
            entry({ id: 1, report_year: 2026, primary_number: "A" }),
            entry({ id: 2, report_year: 2027, primary_number: "B", cost_mio: 500 }),
            entry({ id: 3, report_year: 2027, primary_number: "A" }),
        ]);
        expect(deltas.size).toBe(0);
    });

    it("falls back to the measure name without a number", () => {
        expect(measureKey({ primary_number: null, massnahme: " Knoten Köln ", bezeichnung: null, section: "BP_B", lfd_nr: 3 })).toBe(
            "name:knoten köln",
        );
    });
});

describe("filterRows", () => {
    const rows = [
        { row_key: "a", section: "BP_A", lfd_nr: 1, primary_number: "2-001", bezeichnung: "Hamburg", project_ids: [5] },
        { row_key: "b", section: "BP_A", lfd_nr: 2, primary_number: "2-002", bezeichnung: "Bremen", project_ids: [] },
        { row_key: "c", section: "GVFG_A", lfd_nr: 1, primary_number: "07 D 1", bezeichnung: "S-Bahn", project_ids: [] },
    ] as unknown as InfraplanParsedRow[];

    it("filters by section, assignment and search", () => {
        expect(filterRows(rows, { section: "ALL", onlyUnassigned: false, search: "" })).toHaveLength(3);
        expect(filterRows(rows, { section: "BP_A", onlyUnassigned: true, search: "" }).map((r) => r.row_key)).toEqual(["b"]);
        expect(filterRows(rows, { section: "ALL", onlyUnassigned: false, search: "07 d" }).map((r) => r.row_key)).toEqual([
            "c",
        ]);
    });
});

describe("buildKpiChart", () => {
    const kpi = {
        values: [
            // Ist values of an older year are superseded by the newest year.
            { report_year: 2026, year: 2024, value_kind: "IST", series: null, value: 10 },
            { report_year: 2027, year: 2024, value_kind: "IST", series: "Teil 1", value: 6 },
            { report_year: 2027, year: 2024, value_kind: "IST", series: "Teil 2", value: 5 },
            { report_year: 2026, year: 2027, value_kind: "ZIEL", series: null, value: 30 },
            { report_year: 2027, year: 2027, value_kind: "ZIEL", series: null, value: 25 },
        ],
    } as Pick<InfraplanPublicKpi, "values">;

    it("stacks the newest Ist values and draws one target line per year", () => {
        const chart = buildKpiChart(kpi);
        expect(chart.istReportYear).toBe(2027);
        expect(chart.series.map((s) => s.label)).toEqual([
            "Ist – Teil 1",
            "Ist – Teil 2",
            "Ziel IP 2027",
            "Ziel IP 2026",
        ]);
        expect(chart.series.find((s) => s.label === "Ziel IP 2026")?.strokeDasharray).toBeDefined();
        expect(chart.series.find((s) => s.label === "Ziel IP 2027")?.strokeDasharray).toBeUndefined();
        expect(chart.data).toEqual([
            { year: "2024", "ist|Teil 1": 6, "ist|Teil 2": 5 },
            { year: "2027", "ziel|2026|": 30, "ziel|2027|": 25 },
        ]);
    });

    const split = {
        values: [
            { report_year: 2026, year: 2025, value_kind: "IST", series: "740-m-Netz", value: 4 },
            { report_year: 2026, year: 2025, value_kind: "IST", series: "Stabiles Netz", value: 3 },
            { report_year: 2026, year: 2027, value_kind: "ZIEL", series: "740-m-Netz", value: 2 },
            { report_year: 2026, year: 2027, value_kind: "ZIEL", series: "Stabiles Netz", value: 5 },
        ],
    } as Pick<InfraplanPublicKpi, "values">;

    it("lists the sub-series in order of appearance", () => {
        expect(kpiSubSeries(split)).toEqual(["740-m-Netz", "Stabiles Netz"]);
        expect(kpiSubSeries(kpi)).toEqual(["Teil 1", "Teil 2"]);
    });

    it("sums the sub-series per year for the overview", () => {
        const chart = buildKpiChart(split, "total");
        expect(chart.series.map((s) => s.label)).toEqual(["Ist", "Ziel IP 2026"]);
        expect(chart.data).toEqual([
            { year: "2025", "ist|": 7 },
            { year: "2027", "ziel|2026|": 7 },
        ]);
    });

    it("sums additive sub-series but shows the whole one where configured", () => {
        expect(kpiOverview(split)).toMatchObject({
            scope: "total",
            detailSeries: ["740-m-Netz", "Stabiles Netz"],
            note: "Summe aus 2 Kategorien",
        });
        const etcs = {
            total_series: "Gesamtnetz",
            values: [
                { report_year: 2026, year: 2025, value_kind: "IST", series: "TEN-Kernnetz bis 2030", value: 600 },
                { report_year: 2026, year: 2025, value_kind: "IST", series: "Gesamtnetz", value: 1800 },
            ],
        } as Pick<InfraplanPublicKpi, "values" | "total_series">;
        expect(kpiOverview(etcs)).toMatchObject({
            scope: { series: "Gesamtnetz" },
            detailSeries: ["TEN-Kernnetz bis 2030"],
            note: "Gesamtnetz",
        });
        expect(kpiOverview({ values: [] }).detailSeries).toEqual([]);
    });

    it("draws a companion KPI on the right axis in its own stack", () => {
        const km = {
            unit: "km",
            values: [
                { report_year: 2026, year: 2025, value_kind: "IST", series: "Gesamtnetz", value: 683 },
                { report_year: 2026, year: 2025, value_kind: "IST", series: "TEN-Kernnetz bis 2030", value: 594 },
            ],
        } as Pick<InfraplanPublicKpi, "values" | "unit">;
        const rate = {
            values: [
                { report_year: 2026, year: 2025, value_kind: "IST", series: "Gesamtnetz", value: 2 },
                { report_year: 2026, year: 2025, value_kind: "IST", series: "TEN-Kernnetz bis 2030", value: 5.8 },
            ],
        } as Pick<InfraplanPublicKpi, "values">;
        const chart = buildKpiChart(km, { series: "Gesamtnetz" }, { kpi: rate, label: "Ausrüstungsgrad", unit: "%" });
        expect(chart.series.map((s) => [s.label, s.yAxisId, s.unit])).toEqual([
            ["Ist (km)", undefined, "km"],
            ["Ausrüstungsgrad (%)", "right", "%"],
        ]);
        expect(chart.data).toEqual([{ year: "2025", "ist|": 683, "r:ist|": 2 }]);
    });

    it("pairs each KPI with its configured companion and hides the companion", () => {
        const kpis = [
            { key: "km", name: "km", unit: "km", values: kpi.values, companion_key: "rate", companion_label: null },
            { key: "rate", name: "Ausrüstungsgrad", unit: "%", values: kpi.values, companion_key: null, companion_label: null },
            { key: "empty", name: "x", unit: null, values: [], companion_key: "rate2", companion_label: null },
        ] as Parameters<typeof kpiCompanions>[0];
        const companions = kpiCompanions(kpis);
        expect([...companions.keys()]).toEqual(["km"]);
        expect(companions.get("km")).toMatchObject({ label: "Ausrüstungsgrad", unit: "%" });
        expect([...companionKeys(kpis)]).toEqual(["rate", "rate2"]);
    });

    it("keeps an Ist-only split as a stack", () => {
        expect(kpiOverview(kpi)).toMatchObject({
            layout: "chart",
            scope: "all",
            stacked: true,
            detailSeries: [],
            note: null,
        });
    });

    it("follows chart_layout for non-additive and one-year KPIs", () => {
        expect(kpiOverview({ ...kpi, chart_layout: "grouped" })).toMatchObject({ layout: "chart", stacked: false });
        expect(kpiOverview({ ...kpi, chart_layout: "split" })).toMatchObject({
            layout: "split",
            detailSeries: ["Teil 1", "Teil 2"],
        });
        expect(kpiOverview({ values: [], chart_layout: "flow" }).layout).toBe("flow");
    });

    it("splits a Herkunft/Einsatz KPI into two ranked lists", () => {
        const flow = kpiFlow({
            values: [
                { report_year: 2026, year: 2025, value_kind: "IST", series: "Herkunft: Ländermittel", value: 1.28 },
                { report_year: 2026, year: 2025, value_kind: "IST", series: "Herkunft: Trassenerlöse", value: 6.74 },
                { report_year: 2026, year: 2025, value_kind: "IST", series: "Einsatz: Non-Infra / Sonstige", value: 0.5 },
            ],
        } as Pick<InfraplanPublicKpi, "values">);
        expect(flow).toEqual({
            year: 2025,
            herkunft: [
                { label: "Trassenerlöse", value: 6.74 },
                { label: "Ländermittel", value: 1.28 },
            ],
            einsatz: [{ label: "Non-Infra / Sonstige", value: 0.5 }],
        });
        expect(kpiFlow({ values: [] })).toBeNull();
    });

    it("sums the stacked main-axis bars for the tooltip", () => {
        const series = [
            { name: "ist|SGV", type: "bar" as const },
            { name: "ist|SPNV", type: "bar" as const },
            { name: "r:ist|", type: "bar" as const, yAxisId: "right" as const },
            { name: "ziel|2026|", type: "line" as const },
        ];
        expect(
            stackTotal(
                [
                    { name: "ist|SGV", value: 236 },
                    { name: "ist|SPNV", value: 688 },
                    { name: "r:ist|", value: 2 },
                    { name: "ziel|2026|", value: 900 },
                ],
                series,
            ),
        ).toBe(924);
        expect(stackTotal([{ name: "ist|SGV", value: 236 }], series)).toBeNull();
    });

    it("shows a single sub-series for the detail view", () => {
        const chart = buildKpiChart(split, { series: "Stabiles Netz" });
        expect(chart.series.map((s) => s.label)).toEqual(["Ist", "Ziel IP 2026"]);
        expect(chart.data).toEqual([
            { year: "2025", "ist|": 3 },
            { year: "2027", "ziel|2026|": 5 },
        ]);
    });

    it("is empty without values", () => {
        expect(buildKpiChart({ values: [] })).toEqual({ data: [], series: [], istReportYear: null });
    });
});

describe("groupKpis", () => {
    it("puts Steuerung before Information and sorts within a category", () => {
        const groups = groupKpis([
            { kind: "INFORMATION", category: null, sort_order: 1, name: "I" },
            { kind: "STEUERUNG", category: "BESTANDSNETZ", sort_order: 2, name: "B" },
            { kind: "STEUERUNG", category: "BESTANDSNETZ", sort_order: 1, name: "A" },
            { kind: "STEUERUNG", category: "AUS_NEUBAU", sort_order: 1, name: "N" },
        ]);
        expect(groups.map((g) => g.kind)).toEqual(["STEUERUNG", "INFORMATION"]);
        expect(groups[0].categories.map((c) => c.category)).toEqual(["AUS_NEUBAU", "BESTANDSNETZ"]);
        expect(groups[0].categories[1].kpis.map((k) => k.name)).toEqual(["A", "B"]);
    });
});

describe("zoomedDomain", () => {
    it("starts the axis just below the smallest main-axis value", () => {
        const chart = {
            series: [
                { name: "ist|", label: "Ist", color: "", type: "bar" as const },
                { name: "r:ist|", label: "x", color: "", type: "bar" as const, yAxisId: "right" as const },
            ],
            data: [
                { year: "2024", "ist|": 99.6, "r:ist|": 3 },
                { year: "2025", "ist|": 99.8, "r:ist|": null },
            ],
        };
        expect(zoomedDomain(chart)).toEqual([99, 100]);
        const rate = { ...chart, data: [{ year: "2024", "ist|": 98.9, "r:ist|": null }, { year: "2027", "ist|": 99.8, "r:ist|": null }] };
        expect(zoomedDomain(rate, "%")).toEqual([98, 100]);
        expect(zoomedDomain({ series: [], data: [] })).toBeNull();
    });
});
