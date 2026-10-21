import { describe, expect, it } from "vitest";

import { PHASE_COLOR } from "../../../../shared/theme/semanticColors";
import { MAIN_PHASE_COLOR, MAIN_PHASES, visiblePhases } from "./phaseMeta";

describe("visiblePhases", () => {
    it("returns all main phases when nothing is hidden", () => {
        expect(visiblePhases(undefined)).toEqual(MAIN_PHASES);
        expect(visiblePhases([])).toEqual(MAIN_PHASES);
    });

    it("drops hidden planning phases and keeps the order", () => {
        expect(visiblePhases(["VORPLANUNG", "GENEHMIGUNGSPLANUNG"])).toEqual([
            "NICHT_GESTARTET",
            "BAU",
            "IN_BETRIEB",
        ]);
    });
});

describe("MAIN_PHASE_COLOR", () => {
    it("re-exports the token colours of semanticColors for every phase", () => {
        for (const phase of MAIN_PHASES) {
            expect(MAIN_PHASE_COLOR[phase]).toBe(PHASE_COLOR[phase]);
            expect(MAIN_PHASE_COLOR[phase]).toMatch(/^var\(--idt-[a-z0-9-]+\)$/);
        }
    });

    it("uses green only for In Betrieb", () => {
        const green = MAIN_PHASES.filter((p) => MAIN_PHASE_COLOR[p] === "var(--idt-success)");
        expect(green).toEqual(["IN_BETRIEB"]);
    });
});
