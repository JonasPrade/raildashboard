import { describe, expect, it } from "vitest";

import { applyEditedParts, explodeEditable, parseFeatureList, type EditablePart } from "./editExisting";

const features: GeoJSON.Feature[] = [
    { type: "Feature", geometry: { type: "LineString", coordinates: [[10, 50, 99], [11, 51]] }, properties: { a: 1 } },
    { type: "Feature", geometry: { type: "Point", coordinates: [9, 49] }, properties: { name: "Halle", op_id: "LH" } },
    {
        type: "Feature",
        geometry: { type: "MultiLineString", coordinates: [[[1, 1], [2, 2]], [[3, 3], [4, 4]]] },
        properties: {},
    },
    {
        type: "Feature",
        geometry: { type: "Polygon", coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]] },
        properties: {},
    },
];

function move(part: EditablePart, coordinates: GeoJSON.Position[] | GeoJSON.Position): EditablePart {
    return { ...part, geometry: { ...part.geometry, coordinates } as EditablePart["geometry"] };
}

describe("parseFeatureList", () => {
    it("normalises FeatureCollection, Feature and bare geometry", () => {
        expect(parseFeatureList(JSON.stringify({ type: "FeatureCollection", features }))).toHaveLength(4);
        expect(parseFeatureList(JSON.stringify(features[1]))).toHaveLength(1);
        expect(parseFeatureList(JSON.stringify({ type: "Point", coordinates: [1, 2] }))[0].geometry).toEqual({
            type: "Point",
            coordinates: [1, 2],
        });
        expect(parseFeatureList("nope")).toEqual([]);
        expect(parseFeatureList(null)).toEqual([]);
    });
});

describe("explodeEditable", () => {
    it("creates one part per line/point and skips unsupported geometry", () => {
        const parts = explodeEditable(features);
        expect(parts.map((p) => [p.properties.mode, p.properties.srcIdx, p.properties.srcPart])).toEqual([
            ["linestring", 0, 0],
            ["point", 1, 0],
            ["linestring", 2, 0],
            ["linestring", 2, 1],
        ]);
        // Only 2D positions are handed to terra-draw.
        expect(parts[0].geometry.coordinates).toEqual([[10, 50], [11, 51]]);
    });

    it("rounds coordinates to terra-draw's 9-decimal precision", () => {
        const [part] = explodeEditable([
            { type: "Feature", geometry: { type: "Point", coordinates: [10.12345678912345, 50] }, properties: {} },
        ]);
        expect(part.geometry.coordinates).toEqual([10.123456789, 50]);
    });

    it("skips degenerate lines", () => {
        expect(
            explodeEditable([{ type: "Feature", geometry: { type: "LineString", coordinates: [[1, 1]] }, properties: {} }]),
        ).toEqual([]);
    });
});

describe("applyEditedParts", () => {
    const original = explodeEditable(features);

    it("reports no change and keeps features untouched when nothing moved", () => {
        const { features: out, changed } = applyEditedParts(features, original, original);
        expect(changed).toBe(false);
        expect(out).toEqual(features);
        // Third coordinate survives because the untouched line is not rewritten.
        expect((out[0].geometry as GeoJSON.LineString).coordinates[0]).toEqual([10, 50, 99]);
    });

    it("writes a moved vertex and an inserted midpoint back, keeping properties", () => {
        const edited = [...original];
        edited[0] = move(original[0], [[10, 50], [10.5, 50.6], [11.2, 51]]);
        const { features: out, changed } = applyEditedParts(features, original, edited);
        expect(changed).toBe(true);
        expect(out[0]).toEqual({
            type: "Feature",
            geometry: { type: "LineString", coordinates: [[10, 50], [10.5, 50.6], [11.2, 51]] },
            properties: { a: 1 },
        });
        expect(out[1]).toBe(features[1]);
    });

    it("updates a moved point and a single member of a MultiLineString", () => {
        const edited = [...original];
        edited[1] = move(original[1], [9.1, 49.2]);
        edited[3] = move(original[3], [[3, 3], [4.5, 4.5]]);
        const { features: out } = applyEditedParts(features, original, edited);
        expect(out[1]).toEqual({
            type: "Feature",
            geometry: { type: "Point", coordinates: [9.1, 49.2] },
            properties: { name: "Halle", op_id: "LH" },
        });
        expect((out[2].geometry as GeoJSON.MultiLineString).coordinates).toEqual([
            [[1, 1], [2, 2]],
            [[3, 3], [4.5, 4.5]],
        ]);
        expect(out[3]).toBe(features[3]);
    });

    it("does not mutate the input features", () => {
        const snapshot = JSON.stringify(features);
        const edited = [...original];
        edited[3] = move(original[3], [[0, 0], [5, 5]]);
        applyEditedParts(features, original, edited);
        expect(JSON.stringify(features)).toBe(snapshot);
    });
});
