/** [west, south, east, north] in degrees — the shape maplibre's fitBounds accepts. */
export type LngLatBounds = [number, number, number, number];

type FeatureCollectionLike = {
    features: { geometry?: unknown }[];
};

/**
 * Bounding box over every coordinate of the given feature collections, or
 * null when there is no coordinate at all (project without geometry).
 * Walks GeoJSON coordinate arrays of any depth, so points, lines, polygons
 * and their multi-variants all count.
 */
export function featureBounds(collections: FeatureCollectionLike[]): LngLatBounds | null {
    let west = Infinity;
    let south = Infinity;
    let east = -Infinity;
    let north = -Infinity;

    const visit = (coords: unknown): void => {
        if (!Array.isArray(coords)) return;
        if (typeof coords[0] === "number" && typeof coords[1] === "number") {
            const [lng, lat] = coords as [number, number];
            if (!Number.isFinite(lng) || !Number.isFinite(lat)) return;
            west = Math.min(west, lng);
            east = Math.max(east, lng);
            south = Math.min(south, lat);
            north = Math.max(north, lat);
            return;
        }
        for (const child of coords) visit(child);
    };

    const visitGeometry = (geometry: unknown): void => {
        if (!geometry || typeof geometry !== "object") return;
        const g = geometry as { coordinates?: unknown; geometries?: unknown[] };
        if (Array.isArray(g.geometries)) g.geometries.forEach(visitGeometry);
        else visit(g.coordinates);
    };

    for (const collection of collections) {
        for (const feature of collection.features) visitGeometry(feature.geometry);
    }

    return Number.isFinite(west) ? [west, south, east, north] : null;
}
