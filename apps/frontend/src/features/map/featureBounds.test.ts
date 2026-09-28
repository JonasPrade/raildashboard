import { describe, expect, it } from "vitest";

import { featureBounds } from "./featureBounds";

const fc = (...geometries: unknown[]) => ({
    features: geometries.map((geometry) => ({ geometry })),
});

describe("featureBounds", () => {
    it("spans lines and points across collections", () => {
        const lines = fc({
            type: "MultiLineString",
            coordinates: [
                [[9.9, 53.5], [10.2, 52.4]],
                [[13.4, 52.5], [12.3, 51.3]],
            ],
        });
        const points = fc({ type: "Point", coordinates: [11.6, 48.1] });

        expect(featureBounds([lines, points])).toEqual([9.9, 48.1, 13.4, 53.5]);
    });

    it("collapses to the point for a single station", () => {
        expect(featureBounds([fc({ type: "Point", coordinates: [8.68, 50.11] })])).toEqual([
            8.68, 50.11, 8.68, 50.11,
        ]);
    });

    it("reads geometry collections", () => {
        const collection = fc({
            type: "GeometryCollection",
            geometries: [
                { type: "Point", coordinates: [7, 51] },
                { type: "LineString", coordinates: [[8, 50], [9, 52]] },
            ],
        });
        expect(featureBounds([collection])).toEqual([7, 50, 9, 52]);
    });

    it("returns null without any coordinate", () => {
        expect(featureBounds([fc(), fc(null, { type: "Point", coordinates: [] })])).toBeNull();
    });
});
