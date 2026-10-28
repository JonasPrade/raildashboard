import { describe, expect, it } from "vitest";

import { counterTextColor, groupSharedPoints, majorityColor } from "./mapPoints";
import { MAP_COLOR } from "../../shared/theme/semanticColors";

describe("groupSharedPoints", () => {
    it("merges points of different projects at the same rounded spot", () => {
        const { singles, clusters } = groupSharedPoints([
            { id: 1, groupColor: "#6E50FA", points: [[9.29, 50.26]] },
            { id: 2, groupColor: "#00DCFA", points: [[9.290001, 50.260002], [9.0, 50.4]] },
            { id: 3, groupColor: "#00DCFA", points: [[9.29, 50.26]] },
        ]);
        expect(clusters).toHaveLength(1);
        expect(clusters[0].projectIds).toEqual([1, 2, 3]);
        expect(clusters[0].color).toBe("#00DCFA");
        // Only project 2 keeps a point of its own.
        expect(Object.fromEntries(singles)).toEqual({ 2: [[9.0, 50.4]] });
    });

    it("counts a project once even with several points at the spot", () => {
        const { clusters, singles } = groupSharedPoints([
            { id: 1, points: [[9.0, 50.0], [9.0, 50.0]] },
        ]);
        expect(clusters).toEqual([]);
        expect(singles.get(1)).toHaveLength(2);
    });

    it("keeps points apart that differ beyond the fifth decimal", () => {
        const { clusters } = groupSharedPoints([
            { id: 1, points: [[9.0, 50.0]] },
            { id: 2, points: [[9.00002, 50.0]] },
        ]);
        expect(clusters).toEqual([]);
    });
});

describe("majorityColor", () => {
    it("takes the most frequent colour and the first one on a tie", () => {
        expect(majorityColor(["#A", "#B", "#B"])).toBe("#B");
        expect(majorityColor(["#A", "#B"])).toBe("#A");
        expect(majorityColor([undefined])).toBe(MAP_COLOR.default);
    });
});

describe("counterTextColor", () => {
    it("uses ink on light fills and paper on dark ones", () => {
        expect(counterTextColor("#00DCFA")).toBe(MAP_COLOR.counterRim);
        expect(counterTextColor("#00373C")).toBe(MAP_COLOR.counterTextLight);
    });
});
