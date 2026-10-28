/**
 * Hit testing for the project layers of the map: which projects lie under
 * the pointer. Pure helpers, so the selection logic is testable without
 * a WebGL context (docs/features/feature-map-overlapping-geometries.md → A).
 */

/** Layers whose features stand for projects. Lines and points carry
 *  `projectId`; a station counter (D) carries `clusterId` and stands for
 *  several projects. */
export const PROJECT_LAYERS = ["project-routes-line", "project-points-circle", "project-point-clusters-circle"];

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
 * are both hit, or when a line crosses a tile boundary. A station counter
 * stands for the projects *clusterProjects* names for its `clusterId`.
 */
export function projectIdsFromFeatures(
    features: { properties?: unknown }[],
    clusterProjects?: Map<number, number[]>,
): number[] {
    const ids: number[] = [];
    const seen = new Set<number>();
    const add = (id: number) => {
        if (!Number.isFinite(id) || seen.has(id)) return;
        seen.add(id);
        ids.push(id);
    };
    for (const feature of features) {
        const properties = feature.properties;
        if (typeof properties !== "object" || properties === null) continue;
        const record = properties as Record<string, unknown>;
        if (record.clusterId !== undefined) {
            for (const id of clusterProjects?.get(Number(record.clusterId)) ?? []) add(id);
            continue;
        }
        const value = record.projectId;
        add(typeof value === "number" ? value : Number(value));
    }
    return ids;
}

/** Hits listed by name, independent of the drawing order. */
export function sortProjectsByName<T extends { id: number; name?: string | null }>(projects: T[]): T[] {
    return [...projects].sort(
        (a, b) => (a.name ?? "").localeCompare(b.name ?? "", "de") || a.id - b.id,
    );
}
