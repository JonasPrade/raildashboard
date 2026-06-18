/**
 * Compute the total geodesic length (in kilometres) of all line geometries in a
 * GeoJSON string. Handles FeatureCollection / Feature / bare geometry and sums
 * every LineString and MultiLineString segment via the haversine formula.
 *
 * Returns null when the input cannot be parsed or contains no line geometry.
 */
export function computeGeojsonLengthKm(geojson: string | null | undefined): number | null {
    if (!geojson) return null;
    let parsed: unknown;
    try {
        parsed = JSON.parse(geojson);
    } catch {
        return null;
    }

    const lines = collectLineCoords(parsed);
    if (lines.length === 0) return null;

    let meters = 0;
    for (const coords of lines) {
        for (let i = 1; i < coords.length; i++) {
            meters += haversineMeters(coords[i - 1], coords[i]);
        }
    }
    if (meters <= 0) return null;
    return Math.round((meters / 1000) * 100) / 100;
}

type Position = [number, number, ...number[]];

function collectLineCoords(node: unknown): Position[][] {
    if (!node || typeof node !== "object") return [];
    const g = node as Record<string, unknown>;

    if (g.type === "FeatureCollection" && Array.isArray(g.features)) {
        return (g.features as unknown[]).flatMap(collectLineCoords);
    }
    if (g.type === "Feature") {
        return collectLineCoords(g.geometry);
    }
    if (g.type === "LineString" && Array.isArray(g.coordinates)) {
        return [g.coordinates as Position[]];
    }
    if (g.type === "MultiLineString" && Array.isArray(g.coordinates)) {
        return g.coordinates as Position[][];
    }
    if (g.type === "GeometryCollection" && Array.isArray(g.geometries)) {
        return (g.geometries as unknown[]).flatMap(collectLineCoords);
    }
    return [];
}

function haversineMeters(a: Position, b: Position): number {
    const R = 6371000; // mean earth radius in metres
    const toRad = (deg: number) => (deg * Math.PI) / 180;
    const [lon1, lat1] = a;
    const [lon2, lat2] = b;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const sinLat = Math.sin(dLat / 2);
    const sinLon = Math.sin(dLon / 2);
    const h = sinLat * sinLat + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * sinLon * sinLon;
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
}
