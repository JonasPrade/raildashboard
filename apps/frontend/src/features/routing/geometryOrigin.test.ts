import { describe, expect, it } from "vitest";
import { featureClass, featureOrigin, lineKmByClass, lineKmByOrigin, routeLineFeatures, toggleTrackClass, withOrigin } from "./geometryOrigin";

const COORDS = [[10, 50], [10.02, 50], [10.05, 50], [10.08, 50], [10.1, 50]];

describe("routeLineFeatures", () => {
    it("splits the route by track status and tags the origin", () => {
        const features = routeLineFeatures(COORDS, [
            { track_status: "existing", from_index: 0, to_index: 1, length_km: 1.4 },
            { track_status: "proposed", from_index: 1, to_index: 4, length_km: 5.7 },
        ]);
        expect(features.map((f) => f.geometry.coordinates)).toEqual([COORDS.slice(0, 2), COORDS.slice(1)]);
        expect(features.map((f) => f.properties)).toEqual([
            { geometry_source: "routing", track_status: "existing", railway_class: "rail" },
            { geometry_source: "routing", track_status: "proposed", railway_class: "rail" },
        ]);
    });

    it("keeps a route without sections as one existing-track line", () => {
        const features = routeLineFeatures(COORDS, undefined);
        expect(features).toHaveLength(1);
        expect(featureOrigin(features[0])).toBe("routing_existing");
    });
});

describe("featureOrigin / withOrigin", () => {
    it("reads the stored origin", () => {
        expect(featureOrigin({ properties: { geometry_source: "routing", track_status: "construction" } })).toBe("routing_construction");
        expect(featureOrigin({ properties: { geometry_source: "manual" } })).toBe("manual");
        expect(featureOrigin({ properties: {} })).toBe("unknown");
        expect(featureOrigin(null)).toBe("unknown");
    });

    it("tags lines only and never overwrites an origin", () => {
        const line: GeoJSON.Feature = { type: "Feature", geometry: { type: "LineString", coordinates: COORDS }, properties: { name: "x" } };
        expect(withOrigin(line, "upload").properties).toEqual({ name: "x", geometry_source: "upload" });
        const routed = { ...line, properties: { geometry_source: "routing", track_status: "proposed" } };
        expect(withOrigin(routed, "upload").properties).toEqual(routed.properties);
        const point: GeoJSON.Feature = { type: "Feature", geometry: { type: "Point", coordinates: [10, 50] }, properties: {} };
        expect(withOrigin(point, "manual").properties).toEqual({});
    });
});

describe("lineKmByOrigin", () => {
    it("sums line length per origin in a fixed order", () => {
        const features = [
            ...routeLineFeatures(COORDS, [
                { track_status: "existing", from_index: 0, to_index: 2, length_km: 0 },
                { track_status: "proposed", from_index: 2, to_index: 4, length_km: 0 },
            ]),
            { type: "Feature", geometry: { type: "LineString", coordinates: COORDS }, properties: {} } as GeoJSON.Feature,
        ];
        const totals = lineKmByOrigin(features);
        expect(totals.map((t) => t.origin)).toEqual(["routing_existing", "routing_proposed", "unknown"]);
        expect(totals[2].km).toBeCloseTo(7.2, 1);
    });
});

describe("track classes", () => {
    it("keeps rail exclusive to the urban classes", () => {
        expect(toggleTrackClass(["rail"], "light_rail", true)).toEqual(["light_rail"]);
        expect(toggleTrackClass(["light_rail"], "tram", true)).toEqual(["light_rail", "tram"]);
        expect(toggleTrackClass(["light_rail", "tram"], "rail", true)).toEqual(["rail"]);
        expect(toggleTrackClass(["subway"], "subway", false)).toEqual(["rail"]);
        expect(toggleTrackClass(["rail"], "unknown", true)).toEqual(["rail", "unknown"]);
        expect(toggleTrackClass(["rail", "unknown"], "tram", true)).toEqual(["tram", "unknown"]);
        expect(toggleTrackClass(["rail", "unknown"], "rail", false)).toEqual(["rail", "unknown"]);
    });

    it("tags routed lines with their class and sums km per class", () => {
        const features = routeLineFeatures(COORDS, [
            { track_status: "existing", railway_class: "light_rail", from_index: 0, to_index: 2, length_km: 0 },
            { track_status: "existing", railway_class: "tram", from_index: 2, to_index: 4, length_km: 0 },
        ]);
        expect(features.map(featureClass)).toEqual(["light_rail", "tram"]);
        const drawn = { type: "Feature", geometry: { type: "LineString", coordinates: COORDS }, properties: {} } as GeoJSON.Feature;
        expect(featureClass(drawn)).toBe("none");
        expect(lineKmByClass([...features, drawn]).map((t) => t.cls)).toEqual(["light_rail", "tram", "none"]);
    });
});
