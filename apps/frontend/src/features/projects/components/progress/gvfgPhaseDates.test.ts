import { describe, expect, it } from "vitest";

import type { GvfgProjectEntry } from "../../../../shared/api/queries";
import { gvfgPhaseCompletions } from "./gvfgPhaseDates";

function entry(over: Partial<GvfgProjectEntry> & { year_from?: number }): GvfgProjectEntry {
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

describe("gvfgPhaseCompletions", () => {
    it("reads Baubeginn and Inbetriebnahme tats. as completed phases", () => {
        const result = gvfgPhaseCompletions(
            [entry({ construction_start: 2009, commissioning_actual: 2017 })],
            7,
            [],
            2026,
        );
        expect(result.GENEHMIGUNGSPLANUNG).toEqual({ year: 2009, source: "GVFG 2025–2029, Baubeginn" });
        expect(result.BAU).toEqual({ year: 2017, source: "GVFG 2025–2029, Inbetriebnahme tats." });
    });

    it("ignores future years and other projects' entries", () => {
        const result = gvfgPhaseCompletions(
            [
                entry({ construction_start: 2027, commissioning_actual: 2026 }),
                entry({ key: "other", projects: [{ id: 8, name: "x" }], construction_start: 2000 }),
            ],
            7,
            [],
            2026,
        );
        expect(result).toEqual({});
    });

    it("uses the newest edition and moves the Baubeginn past hidden phases", () => {
        const result = gvfgPhaseCompletions(
            [entry({ year_from: 2020, construction_start: 2008 }), entry({ construction_start: 2010 })],
            7,
            ["GENEHMIGUNGSPLANUNG"],
            2026,
        );
        expect(result).toEqual({ VORPLANUNG: { year: 2010, source: "GVFG 2025–2029, Baubeginn" } });
    });
});
