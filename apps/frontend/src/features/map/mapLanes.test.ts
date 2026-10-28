import { describe, expect, it } from "vitest";

import { assignVisibleLanes, laneOffset, lineOffsetExpression } from "./mapLanes";

describe("assignVisibleLanes", () => {
    it("follows the stored order and packs the lanes", () => {
        const lanes = assignVisibleLanes([
            { id: 1, mapLane: { lane: 0, overlaps: [2, 3] } },
            { id: 2, mapLane: { lane: 1, overlaps: [1] } },
            { id: 3, mapLane: { lane: 2, overlaps: [1] } },
        ]);
        // 3 does not overlap 2, so it can share lane 1 beside 1.
        expect(Object.fromEntries(lanes)).toEqual({ 1: 0, 2: 1, 3: 1 });
    });

    it("puts a project back on the track when its partner is not shown", () => {
        const lanes = assignVisibleLanes([{ id: 2, mapLane: { lane: 1, overlaps: [1] } }]);
        expect(lanes.get(2)).toBe(0);
    });

    it("separates partners from two groups shown together", () => {
        const lanes = assignVisibleLanes([
            { id: 5, mapLane: { lane: 0, overlaps: [9] } },
            { id: 9, mapLane: { lane: 0, overlaps: [5] } },
        ]);
        expect([lanes.get(5), lanes.get(9)]).toEqual([0, 1]);
    });

    it("gives a triangle three lanes and projects without data lane 0", () => {
        const lanes = assignVisibleLanes([
            { id: 1, mapLane: { lane: 0, overlaps: [2, 3] } },
            { id: 2, mapLane: { lane: 1, overlaps: [1, 3] } },
            { id: 3, mapLane: { lane: 2, overlaps: [1, 2] } },
            { id: 4 },
        ]);
        expect(Object.fromEntries(lanes)).toEqual({ 1: 0, 2: 1, 3: 2, 4: 0 });
    });
});

describe("laneOffset", () => {
    it("alternates right and left, moving out every second lane", () => {
        expect([0, 1, 2, 3, 4, 5].map(laneOffset)).toEqual([0, 1, -1, 2, -2, 3]);
    });
});

describe("lineOffsetExpression", () => {
    it("interpolates over zoom at the top level and scales with the line width", () => {
        const expression = lineOffsetExpression(6);
        expect(expression.slice(0, 3)).toEqual(["interpolate", ["linear"], ["zoom"]]);
        expect(expression[expression.length - 1]).toEqual([
            "*",
            ["coalesce", ["get", "laneOffset"], 0],
            8,
        ]);
    });
});
