import { describe, expect, it } from "vitest";

import {
    PHASE_UNKNOWN,
    filterProjectsByPhase,
    parsePhaseParam,
    phaseFilterKey,
    phaseFilterOptions,
    serializePhaseParam,
} from "./phaseFilter";

const PROJECTS = [
    { id: 1, name: "Bau aktiv", headline_phase: "BAU", lifecycle_status: "AKTIV" },
    { id: 2, name: "Bau pausiert", headline_phase: "BAU", lifecycle_status: "PAUSIERT" },
    { id: 3, name: "Vorplanung", headline_phase: "VORPLANUNG", lifecycle_status: "AKTIV" },
    { id: 4, name: "Ohne Phase", headline_phase: null, lifecycle_status: "AKTIV" },
    { id: 5, name: "Ohne Progress-Zeile", headline_phase: null, lifecycle_status: null },
    { id: 6, name: "Feld fehlt" },
];

const ids = (projects: { id: number }[]) => projects.map((p) => p.id);

describe("parsePhaseParam", () => {
    it("returns an empty selection for a missing or empty param", () => {
        expect(parsePhaseParam(null)).toEqual([]);
        expect(parsePhaseParam("")).toEqual([]);
        expect(parsePhaseParam(" , ")).toEqual([]);
    });

    it("keeps valid values in canonical order, deduplicated", () => {
        expect(parsePhaseParam("UNBEKANNT,BAU,VORPLANUNG,BAU")).toEqual(["VORPLANUNG", "BAU", PHASE_UNKNOWN]);
    });

    it("drops unknown tokens and tolerates case and whitespace", () => {
        expect(parsePhaseParam(" bau ,LP3,in_betrieb")).toEqual(["BAU", "IN_BETRIEB"]);
    });
});

describe("serializePhaseParam", () => {
    it("normalises the selection for the URL", () => {
        expect(serializePhaseParam(["UNBEKANNT", "BAU", "NICHT_GESTARTET"])).toBe("NICHT_GESTARTET,BAU,UNBEKANNT");
    });

    it("returns null for an empty selection so the param is removed", () => {
        expect(serializePhaseParam([])).toBeNull();
        expect(serializePhaseParam(["QUATSCH"])).toBeNull();
    });

    it("round-trips through parsePhaseParam", () => {
        const raw = serializePhaseParam(["IN_BETRIEB", "GENEHMIGUNGSPLANUNG"]);
        expect(parsePhaseParam(raw)).toEqual(["GENEHMIGUNGSPLANUNG", "IN_BETRIEB"]);
    });
});

describe("phaseFilterKey", () => {
    it("buckets missing, null and invalid phases as unknown", () => {
        expect(phaseFilterKey({ headline_phase: "BAU" })).toBe("BAU");
        expect(phaseFilterKey({ headline_phase: null })).toBe(PHASE_UNKNOWN);
        expect(phaseFilterKey({})).toBe(PHASE_UNKNOWN);
        expect(phaseFilterKey({ headline_phase: "KAPUTT" })).toBe(PHASE_UNKNOWN);
        expect(phaseFilterKey({ headline_phase: PHASE_UNKNOWN })).toBe(PHASE_UNKNOWN);
    });
});

describe("filterProjectsByPhase", () => {
    it("returns the same array when nothing is selected", () => {
        expect(filterProjectsByPhase(PROJECTS, [])).toBe(PROJECTS);
    });

    it("filters by headline phase, including paused projects", () => {
        expect(ids(filterProjectsByPhase(PROJECTS, ["BAU"]))).toEqual([1, 2]);
    });

    it("selects projects without a phase through the unknown option", () => {
        expect(ids(filterProjectsByPhase(PROJECTS, [PHASE_UNKNOWN]))).toEqual([4, 5, 6]);
    });

    it("combines several phases with OR", () => {
        expect(ids(filterProjectsByPhase(PROJECTS, ["VORPLANUNG", PHASE_UNKNOWN]))).toEqual([3, 4, 5, 6]);
    });

    it("returns nothing when no project is in the selected phase", () => {
        expect(filterProjectsByPhase(PROJECTS, ["IN_BETRIEB"])).toEqual([]);
    });
});

describe("phaseFilterOptions", () => {
    it("lists the five phases in order plus Unbekannt with German labels", () => {
        expect(phaseFilterOptions()).toEqual([
            { value: "NICHT_GESTARTET", label: "Nicht gestartet" },
            { value: "VORPLANUNG", label: "Vorplanung" },
            { value: "GENEHMIGUNGSPLANUNG", label: "Genehmigungsplanung" },
            { value: "BAU", label: "Bau" },
            { value: "IN_BETRIEB", label: "In Betrieb" },
            { value: "UNBEKANNT", label: "Unbekannt" },
        ]);
    });
});
