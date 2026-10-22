import { describe, expect, it } from "vitest";

import type { GvfgProjectEntry, VibEntryForProject } from "../../../../shared/api/queries";
import { gvfgPhaseCompletions, mergeCompletions, vibDateEnd, vibPhaseCompletions } from "./phaseCompletions";

function gvfg(over: Partial<GvfgProjectEntry> & { year_from?: number }): GvfgProjectEntry {
    const { year_from = 2025, ...rest } = over;
    return {
        id: 1,
        key: "08 G 174_T",
        projects: [{ id: 7, name: "U12" }],
        program: { year_from, year_to: year_from + 4 },
        construction_start: null,
        commissioning_actual: null,
        ...rest,
    } as unknown as GvfgProjectEntry;
}

function vib(year: number, pfas: Record<string, unknown>[]): VibEntryForProject {
    return {
        id: year,
        year,
        project_ids: [7],
        pfa_entries: pfas.map((p, i) => ({ id: i, project_id: null, ...p })),
    } as unknown as VibEntryForProject;
}

describe("gvfgPhaseCompletions", () => {
    it("reads Baubeginn and Inbetriebnahme tats. as completed phases", () => {
        const result = gvfgPhaseCompletions(
            [gvfg({ construction_start: 2009, commissioning_actual: 2017 })],
            7,
            [],
            2026,
        );
        expect(result.GENEHMIGUNGSPLANUNG).toEqual([{ label: "2009", source: "GVFG 2025–2029, Baubeginn" }]);
        expect(result.BAU).toEqual([{ label: "2017", source: "GVFG 2025–2029, Inbetriebnahme tats." }]);
    });

    it("ignores future years and other projects' entries", () => {
        const result = gvfgPhaseCompletions(
            [
                gvfg({ construction_start: 2027, commissioning_actual: 2026 }),
                gvfg({ key: "other", projects: [{ id: 8, name: "x" }], construction_start: 2000 }),
            ],
            7,
            [],
            2026,
        );
        expect(result).toEqual({});
    });

    it("uses the newest edition and moves the Baubeginn past hidden phases", () => {
        const result = gvfgPhaseCompletions(
            [gvfg({ year_from: 2020, construction_start: 2008 }), gvfg({ construction_start: 2010 })],
            7,
            ["GENEHMIGUNGSPLANUNG"],
            2026,
        );
        expect(result).toEqual({ VORPLANUNG: [{ label: "2010", source: "GVFG 2025–2029, Baubeginn" }] });
    });
});

describe("vibDateEnd", () => {
    it("returns the end of the named period", () => {
        expect(vibDateEnd("01.03.2024")).toEqual(new Date(2024, 2, 1));
        expect(vibDateEnd("12/2024")).toEqual(new Date(2024, 11, 31));
        expect(vibDateEnd("2. Quartal 2025")).toEqual(new Date(2025, 5, 30));
        expect(vibDateEnd("Mitte 2026")).toEqual(new Date(2026, 7, 31));
        expect(vibDateEnd("März 2024")).toEqual(new Date(2024, 2, 31));
        expect(vibDateEnd("2019")).toEqual(new Date(2019, 11, 31));
        expect(vibDateEnd("-")).toBeNull();
    });
});

describe("vibPhaseCompletions", () => {
    const today = new Date(2026, 9, 22);

    it("takes the latest section date of the newest report", () => {
        const result = vibPhaseCompletions(
            [
                vib(2023, [
                    { datum_pfb: "03/2015", inbetriebnahme: "12/2020" },
                    { datum_pfb: "2016", baubeginn: "2017", inbetriebnahme: "06.05.2022" },
                ]),
                vib(2019, [{ datum_pfb: "2000" }]),
            ],
            7,
            false,
            [],
            today,
        );
        expect(result.GENEHMIGUNGSPLANUNG).toEqual([{ label: "2016", source: "VIB 2023, PFB bzw. Baubeginn, 2 Abschnitte" }]);
        expect(result.BAU).toEqual([{ label: "06.05.2022", source: "VIB 2023, Inbetriebnahme, 2 Abschnitte" }]);
    });

    it("needs every section done and skips forecasts", () => {
        const result = vibPhaseCompletions(
            [
                vib(2023, [
                    { datum_pfb: "2015", inbetriebnahme: "2020" },
                    { datum_pfb: "voraussichtlich 2016", inbetriebnahme: null },
                ]),
            ],
            7,
            false,
            [],
            today,
        );
        expect(result).toEqual({});
    });

    it("leaves out sections assigned to other projects on a leaf", () => {
        const result = vibPhaseCompletions(
            [vib(2023, [{ datum_pfb: "2015" }, { datum_pfb: null, project_id: 8 }])],
            7,
            false,
            [],
            today,
        );
        expect(result.GENEHMIGUNGSPLANUNG?.[0].label).toBe("2015");
    });
});

describe("mergeCompletions", () => {
    it("keeps every source per phase", () => {
        const a = { BAU: [{ label: "2017", source: "GVFG" }] };
        const b = { BAU: [{ label: "2018", source: "VIB" }] };
        expect(mergeCompletions(a, b).BAU).toHaveLength(2);
    });
});
