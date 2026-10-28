/**
 * Parallel lanes for projects that share a track
 * (docs/features/feature-map-overlapping-geometries.md → B1).
 *
 * The server stores a lane per project and names its overlap partners. The map
 * colours only the projects it currently shows, so a project whose partner is
 * filtered out stays on the track (W1). Order: stored lane, then id; each
 * project takes the smallest lane no visible partner holds, so the stored
 * order decides who stays on the track and lanes stay packed.
 */

export type LaneInfo = { lane?: number | null; overlaps?: number[] | null };

type LaneProject = { id: number; mapLane?: LaneInfo | null };

/** Lane per visible project; projects without partners on the map get 0. */
export function assignVisibleLanes(projects: LaneProject[]): Map<number, number> {
    const visible = new Set(projects.map((p) => p.id));
    const lanes = new Map<number, number>();
    const ordered = projects
        .filter((p) => (p.mapLane?.overlaps ?? []).some((id) => visible.has(id)))
        .sort((a, b) => (a.mapLane?.lane ?? 0) - (b.mapLane?.lane ?? 0) || a.id - b.id);
    for (const project of ordered) {
        const taken = new Set<number>();
        for (const partner of project.mapLane?.overlaps ?? []) {
            const lane = lanes.get(partner);
            if (lane !== undefined) taken.add(lane);
        }
        let lane = 0;
        while (taken.has(lane)) lane += 1;
        lanes.set(project.id, lane);
    }
    for (const project of projects) {
        if (!lanes.has(project.id)) lanes.set(project.id, 0);
    }
    return lanes;
}

/**
 * Side and distance of a lane in multiples of the lane gap: 0 stays on the
 * track, 1 right, 2 left, 3 twice right, 4 twice left, …
 */
export function laneOffset(lane: number): number {
    if (lane <= 0) return 0;
    return lane % 2 === 1 ? Math.ceil(lane / 2) : -(lane / 2);
}

/**
 * `line-offset` expression: lines lie on top of each other when zoomed out and
 * fan out up to `lineWidth + 2` px per lane from zoom 12. `zoom` may only be
 * the input of the outermost interpolate, so the data part sits in the stop.
 */
export function lineOffsetExpression(lineWidth: number) {
    return [
        "interpolate",
        ["linear"],
        ["zoom"],
        8,
        0,
        12,
        ["*", ["coalesce", ["get", "laneOffset"], 0], lineWidth + 2],
    ];
}
