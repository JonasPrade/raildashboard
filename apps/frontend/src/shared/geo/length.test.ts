import { describe, expect, it } from "vitest";

import { computeGeojsonLengthKm } from "./length";

describe("computeGeojsonLengthKm", () => {
    it("returns null for empty / invalid input", () => {
        expect(computeGeojsonLengthKm(null)).toBeNull();
        expect(computeGeojsonLengthKm("")).toBeNull();
        expect(computeGeojsonLengthKm("not json")).toBeNull();
    });

    it("returns null when there is no line geometry", () => {
        const pointFc = JSON.stringify({
            type: "FeatureCollection",
            features: [{ type: "Feature", geometry: { type: "Point", coordinates: [10, 51] }, properties: {} }],
        });
        expect(computeGeojsonLengthKm(pointFc)).toBeNull();
    });

    it("computes ~1° of longitude at the equator (~111 km)", () => {
        const line = JSON.stringify({
            type: "LineString",
            coordinates: [[0, 0], [1, 0]],
        });
        const km = computeGeojsonLengthKm(line);
        expect(km).not.toBeNull();
        expect(km!).toBeGreaterThan(110);
        expect(km!).toBeLessThan(112);
    });

    it("sums multiple line features in a FeatureCollection", () => {
        const fc = JSON.stringify({
            type: "FeatureCollection",
            features: [
                { type: "Feature", geometry: { type: "LineString", coordinates: [[0, 0], [1, 0]] }, properties: {} },
                { type: "Feature", geometry: { type: "LineString", coordinates: [[1, 0], [2, 0]] }, properties: {} },
            ],
        });
        const km = computeGeojsonLengthKm(fc);
        expect(km!).toBeGreaterThan(221);
        expect(km!).toBeLessThan(223);
    });
});
