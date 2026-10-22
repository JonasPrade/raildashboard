import { describe, expect, it } from "vitest";

import { nextSort, sortProjects } from "./projectListSort";

const P = [
    { name: "Würzburg", headline_phase: "BAU", length: 12 },
    { name: "aachen", headline_phase: null, length: null },
    { name: "Bremen", headline_phase: "VORPLANUNG", length: 40 },
    { name: "Ägypten", headline_phase: "IN_BETRIEB", length: 3 },
];
const names = (list: typeof P) => list.map((p) => p.name);

describe("sortProjects", () => {
    it("keeps the incoming order without a key", () => {
        expect(names(sortProjects(P, { key: null, dir: "asc" }))).toEqual(names(P));
    });

    it("sorts names German-style, case-insensitive", () => {
        expect(names(sortProjects(P, { key: "name", dir: "asc" }))).toEqual(["aachen", "Ägypten", "Bremen", "Würzburg"]);
        expect(names(sortProjects(P, { key: "name", dir: "desc" }))).toEqual(["Würzburg", "Bremen", "Ägypten", "aachen"]);
    });

    it("sorts phases in planning order, unknown last in both directions", () => {
        expect(names(sortProjects(P, { key: "phase", dir: "asc" }))).toEqual(["Bremen", "Würzburg", "Ägypten", "aachen"]);
        expect(names(sortProjects(P, { key: "phase", dir: "desc" }))).toEqual(["Ägypten", "Würzburg", "Bremen", "aachen"]);
    });

    it("sorts lengths numerically, missing last", () => {
        expect(names(sortProjects(P, { key: "length", dir: "desc" }))).toEqual(["Bremen", "Würzburg", "Ägypten", "aachen"]);
    });

    it("does not mutate its input", () => {
        const copy = [...P];
        sortProjects(P, { key: "name", dir: "asc" });
        expect(P).toEqual(copy);
    });
});

describe("sortProjects by dates", () => {
    it("orders by the Baubeginn sort value, undated last", () => {
        const rows = [
            { name: "offen", construction_start_date: "2032-01-01" },
            { name: "ohne", construction_start_date: null },
            { name: "2028", construction_start_date: "2028-01-01" },
        ];
        expect(sortProjects(rows, { key: "dates", dir: "asc" }).map((r) => r.name)).toEqual(["2028", "offen", "ohne"]);
        expect(sortProjects(rows, { key: "dates", dir: "desc" }).map((r) => r.name)).toEqual(["offen", "2028", "ohne"]);
    });
});

describe("nextSort", () => {
    it("flips the direction on the same column and starts ascending on another", () => {
        expect(nextSort({ key: "name", dir: "asc" }, "name")).toEqual({ key: "name", dir: "desc" });
        expect(nextSort({ key: "name", dir: "desc" }, "length")).toEqual({ key: "length", dir: "asc" });
        expect(nextSort({ key: null, dir: "asc" }, "phase")).toEqual({ key: "phase", dir: "asc" });
    });
});
