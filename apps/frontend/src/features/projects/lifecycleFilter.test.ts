import { describe, expect, it } from "vitest";

import { filterEndedProjects, parseShowEnded } from "./lifecycleFilter";

const projects = [
    { id: 1, lifecycle_status: "AKTIV" },
    { id: 2, lifecycle_status: "PAUSIERT" },
    { id: 3, lifecycle_status: "ABGEBROCHEN" },
    { id: 4, lifecycle_status: "ERSETZT" },
    { id: 5, lifecycle_status: null },
];

describe("lifecycleFilter", () => {
    it("hides aborted and replaced projects by default", () => {
        expect(filterEndedProjects(projects, false).map((p) => p.id)).toEqual([1, 2, 5]);
    });

    it("shows everything when switched on", () => {
        expect(filterEndedProjects(projects, true)).toBe(projects);
    });

    it("returns the same array when nothing is hidden", () => {
        const active = projects.slice(0, 2);
        expect(filterEndedProjects(active, false)).toBe(active);
    });

    it("reads only `1` as switched on", () => {
        expect(parseShowEnded("1")).toBe(true);
        expect(parseShowEnded(null)).toBe(false);
        expect(parseShowEnded("0")).toBe(false);
    });
});
