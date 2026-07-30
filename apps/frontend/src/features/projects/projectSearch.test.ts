import { describe, expect, it } from "vitest";

import {
    collectSubtreeIds,
    normalizeSearchText,
    searchProjects,
    type SearchableProject,
} from "./projectSearch";

const PROJECTS: SearchableProject[] = [
    { id: 1, name: "ABS Hamburg–Lübeck", project_number: "2-001" },
    { id: 2, name: "Ausbau Lübeck Hbf", project_number: "2-002", superior_project_id: 1 },
    { id: 3, name: "Elektrifizierung Lübeck–Puttgarden", project_number: "2-003", superior_project_id: 2 },
    { id: 4, name: "NBS Hannover–Bielefeld", project_number: "3-010" },
];

const names = (projects: SearchableProject[]) => projects.map((p) => p.name);

describe("normalizeSearchText", () => {
    it("folds diacritics, ß and punctuation", () => {
        expect(normalizeSearchText("ABS Hamburg–Lübeck")).toBe("abs hamburg lubeck");
        expect(normalizeSearchText("Straßen-Ausbau")).toBe("strassen ausbau");
        expect(normalizeSearchText(null)).toBe("");
    });
});

describe("searchProjects", () => {
    it("returns every project for an empty query", () => {
        expect(searchProjects(PROJECTS, "  ")).toHaveLength(4);
    });

    it("matches without umlauts and across dash variants", () => {
        expect(names(searchProjects(PROJECTS, "hamburg-lubeck"))).toEqual(["ABS Hamburg–Lübeck"]);
    });

    it("matches tokens in any order", () => {
        expect(names(searchProjects(PROJECTS, "lubeck abs"))).toEqual(["ABS Hamburg–Lübeck"]);
    });

    it("matches the project number", () => {
        expect(names(searchProjects(PROJECTS, "2-003"))).toEqual([
            "Elektrifizierung Lübeck–Puttgarden",
        ]);
    });

    it("ranks equally good hits by name length, shortest first", () => {
        expect(names(searchProjects(PROJECTS, "lubeck"))).toEqual([
            "Ausbau Lübeck Hbf", // word-boundary hit, shortest name
            "ABS Hamburg–Lübeck",
            "Elektrifizierung Lübeck–Puttgarden",
        ]);
    });

    it("drops excluded ids", () => {
        const excluded = searchProjects(PROJECTS, "lubeck", { excludeIds: new Set([1, 2]) });
        expect(names(excluded)).toEqual(["Elektrifizierung Lübeck–Puttgarden"]);
    });

    it("returns nothing when no token matches", () => {
        expect(searchProjects(PROJECTS, "flughafen")).toEqual([]);
    });
});

describe("collectSubtreeIds", () => {
    it("collects the project and all its descendants", () => {
        expect([...collectSubtreeIds(PROJECTS, 1)].sort()).toEqual([1, 2, 3]);
    });

    it("collects only the project itself when it has no children", () => {
        expect([...collectSubtreeIds(PROJECTS, 4)]).toEqual([4]);
    });

    it("is empty without a root", () => {
        expect(collectSubtreeIds(PROJECTS, null).size).toBe(0);
    });

    it("terminates on a pre-existing cycle in the data", () => {
        const cyclic: SearchableProject[] = [
            { id: 1, name: "A", superior_project_id: 2 },
            { id: 2, name: "B", superior_project_id: 1 },
        ];
        expect([...collectSubtreeIds(cyclic, 1)].sort()).toEqual([1, 2]);
    });
});
