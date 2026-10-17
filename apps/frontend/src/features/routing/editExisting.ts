/**
 * Helpers for editing already-saved project geometry in place.
 *
 * terra-draw only edits plain LineString and Point features, so the saved geometry is
 * exploded into editable "parts" (one per LineString / Point, one per member of a
 * MultiLineString / MultiPoint). Each part remembers where it came from (`srcIdx` = index
 * of the feature in the saved FeatureCollection, `srcPart` = index inside a Multi*
 * geometry). After editing, the parts are written back into the original features, so
 * feature order, properties (e.g. operational-point names) and untouched geometry stay
 * exactly as they were.
 */

/** terra-draw rejects coordinates with more than 9 decimals (its default coordinatePrecision). */
const PRECISION = 1e9;

export type EditablePart = GeoJSON.Feature<
    GeoJSON.LineString | GeoJSON.Point,
    { mode: "linestring" | "point"; srcIdx: number; srcPart: number }
>;

/**
 * Parse a GeoJSON string into a flat list of Features. Accepts a FeatureCollection,
 * a bare Feature, or a bare Geometry (wrapped into a Feature). Returns [] on parse error.
 */
export function parseFeatureList(raw: string | null | undefined): GeoJSON.Feature[] {
    if (!raw) return [];
    try {
        const p = JSON.parse(raw);
        if (p && p.type === "FeatureCollection") return (p.features ?? []) as GeoJSON.Feature[];
        if (p && p.type === "Feature") return [p as GeoJSON.Feature];
        if (p && typeof p.type === "string") return [{ type: "Feature", geometry: p, properties: {} }];
    } catch { /* ignore */ }
    return [];
}

function isPosition(c: unknown): c is number[] {
    return Array.isArray(c) && c.length >= 2 && Number.isFinite(c[0]) && Number.isFinite(c[1]);
}

function toPosition(c: number[]): GeoJSON.Position {
    return [Math.round(c[0] * PRECISION) / PRECISION, Math.round(c[1] * PRECISION) / PRECISION];
}

function toLine(coords: unknown): GeoJSON.Position[] | null {
    if (!Array.isArray(coords) || coords.length < 2 || !coords.every(isPosition)) return null;
    return coords.map(toPosition);
}

/** Explode saved features into terra-draw-editable LineString/Point parts. */
export function explodeEditable(features: GeoJSON.Feature[]): EditablePart[] {
    const parts: EditablePart[] = [];
    const pushLine = (coords: unknown, srcIdx: number, srcPart: number) => {
        const line = toLine(coords);
        if (line) {
            parts.push({
                type: "Feature",
                geometry: { type: "LineString", coordinates: line },
                properties: { mode: "linestring", srcIdx, srcPart },
            });
        }
    };
    const pushPoint = (coords: unknown, srcIdx: number, srcPart: number) => {
        if (isPosition(coords)) {
            parts.push({
                type: "Feature",
                geometry: { type: "Point", coordinates: toPosition(coords) },
                properties: { mode: "point", srcIdx, srcPart },
            });
        }
    };

    features.forEach((f, srcIdx) => {
        const g = f?.geometry;
        if (!g) return;
        if (g.type === "LineString") pushLine(g.coordinates, srcIdx, 0);
        else if (g.type === "MultiLineString") g.coordinates.forEach((c, i) => pushLine(c, srcIdx, i));
        else if (g.type === "Point") pushPoint(g.coordinates, srcIdx, 0);
        else if (g.type === "MultiPoint") g.coordinates.forEach((c, i) => pushPoint(c, srcIdx, i));
    });
    return parts;
}

function sameCoords(a: unknown, b: unknown): boolean {
    return JSON.stringify(a) === JSON.stringify(b);
}

/**
 * Write edited parts back into the saved features. Only parts whose coordinates differ
 * from their original (`originalParts`) are applied, so untouched geometry is kept
 * byte-for-byte (including any third coordinate or extra precision). Parts missing from
 * `editedParts` are left unchanged — deleting whole features happens elsewhere.
 */
export function applyEditedParts(
    features: GeoJSON.Feature[],
    originalParts: EditablePart[],
    editedParts: EditablePart[],
): { features: GeoJSON.Feature[]; changed: boolean } {
    const key = (p: EditablePart) => `${p.properties.srcIdx}:${p.properties.srcPart}`;
    const originals = new Map(originalParts.map((p) => [key(p), p]));

    const result = features.map((f) => f);
    let changed = false;

    for (const part of editedParts) {
        const original = originals.get(key(part));
        if (!original || sameCoords(original.geometry.coordinates, part.geometry.coordinates)) continue;

        const { srcIdx, srcPart } = part.properties;
        const feature = result[srcIdx];
        const g = feature?.geometry;
        if (!g) continue;

        let geometry: GeoJSON.Geometry | null = null;
        if (g.type === "LineString" && part.geometry.type === "LineString") {
            geometry = { type: "LineString", coordinates: part.geometry.coordinates };
        } else if (g.type === "MultiLineString" && part.geometry.type === "LineString") {
            const coordinates = [...g.coordinates];
            coordinates[srcPart] = part.geometry.coordinates;
            geometry = { type: "MultiLineString", coordinates };
        } else if (g.type === "Point" && part.geometry.type === "Point") {
            geometry = { type: "Point", coordinates: part.geometry.coordinates };
        } else if (g.type === "MultiPoint" && part.geometry.type === "Point") {
            const coordinates = [...g.coordinates];
            coordinates[srcPart] = part.geometry.coordinates;
            geometry = { type: "MultiPoint", coordinates };
        }
        if (!geometry) continue;

        result[srcIdx] = { ...feature, geometry };
        changed = true;
    }

    return { features: result, changed };
}
