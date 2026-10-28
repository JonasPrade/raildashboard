/**
 * Hit testing for the project layers of the map: which projects lie under
 * the pointer. Pure helpers, so the selection logic is testable without
 * a WebGL context (docs/features/feature-map-overlapping-geometries.md → A).
 */

/** Layers whose features stand for projects; every feature carries `projectId`. */
export const PROJECT_LAYERS = ["project-routes-line", "project-points-circle"];

/** Half the side of the square queried around the pointer, in px. A finger
 *  needs more room than a mouse to hit a 4 px line or a neighbouring lane. */
export function hitTolerancePx(coarsePointer: boolean): number {
    return coarsePointer ? 8 : 4;
}

export function isCoarsePointer(): boolean {
    return typeof window !== "undefined" && typeof window.matchMedia === "function"
        ? window.matchMedia("(pointer: coarse)").matches
        : false;
}

/** Screen box around *point*, in the `[[x1, y1], [x2, y2]]` form
 *  `queryRenderedFeatures` accepts. */
export function hitBox(
    point: { x: number; y: number },
    tolerance: number,
): [[number, number], [number, number]] {
    return [
        [point.x - tolerance, point.y - tolerance],
        [point.x + tolerance, point.y + tolerance],
    ];
}

/**
 * Project ids of the rendered features, each once, in the order of their
 * first hit. A project shows up several times when its line and its points
 * are both hit, or when a line crosses a tile boundary.
 */
export function projectIdsFromFeatures(features: { properties?: unknown }[]): number[] {
    const ids: number[] = [];
    const seen = new Set<number>();
    for (const feature of features) {
        const properties = feature.properties;
        if (typeof properties !== "object" || properties === null) continue;
        const value = (properties as Record<string, unknown>).projectId;
        const id = typeof value === "number" ? value : Number(value);
        if (!Number.isFinite(id) || seen.has(id)) continue;
        seen.add(id);
        ids.push(id);
    }
    return ids;
}

/** Hits listed by name, independent of the drawing order. */
export function sortProjectsByName<T extends { id: number; name?: string | null }>(projects: T[]): T[] {
    return [...projects].sort(
        (a, b) => (a.name ?? "").localeCompare(b.name ?? "", "de") || a.id - b.id,
    );
}
