import { describe, expect, it } from "vitest";

import { MAIN_PHASES, visiblePhases } from "./phaseMeta";

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
