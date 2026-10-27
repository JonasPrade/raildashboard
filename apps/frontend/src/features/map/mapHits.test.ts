import { describe, expect, it } from "vitest";

import { hitBox, hitTolerancePx, projectIdsFromFeatures, sortProjectsByName } from "./mapHits";

describe("projectIdsFromFeatures", () => {
    it("keeps each project once, in the order of its first hit", () => {
        const features = [
            { properties: { projectId: 7 } },
            { properties: { projectId: 3 } },
            { properties: { projectId: 7 } },
            { properties: { projectId: "3" } },
            { properties: { projectId: 11 } },
        ];
        expect(projectIdsFromFeatures(features)).toEqual([7, 3, 11]);
    });

    it("skips features without a usable project id", () => {
        const features = [
            { properties: null },
            {},
            { properties: { projectId: "abc" } },
            { properties: { other: 1 } },
            { properties: { projectId: 5 } },
        ];
        expect(projectIdsFromFeatures(features)).toEqual([5]);
    });
});

describe("hitBox", () => {
    it("spans the tolerance on every side of the point", () => {
        expect(hitBox({ x: 100, y: 50 }, 4)).toEqual([
            [96, 46],
            [104, 54],
        ]);
    });

    it("gives a finger more room than a mouse", () => {
        expect(hitTolerancePx(true)).toBeGreaterThan(hitTolerancePx(false));
    });
});

describe("sortProjectsByName", () => {
    it("sorts by name with German collation, then by id", () => {
        const projects = [
            { id: 3, name: "Zwickau" },
            { id: 2, name: "Ölde" },
            { id: 9, name: "Aachen" },
            { id: 1, name: "Aachen" },
            { id: 4, name: null },
        ];
        expect(sortProjectsByName(projects).map((p) => p.id)).toEqual([4, 1, 9, 2, 3]);
    });
});

describe("projectIdsFromFeatures with station counters", () => {
    it("expands a counter into its projects", () => {
        const clusters = new Map([[1, [4, 5, 6]]]);
        const features = [
            { properties: { projectId: 5 } },
            { properties: { clusterId: 1, count: 3 } },
            { properties: { clusterId: 99 } },
        ];
        expect(projectIdsFromFeatures(features, clusters)).toEqual([5, 4, 6]);
    });
});
