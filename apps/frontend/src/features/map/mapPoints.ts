/**
 * Station counters: points of several projects at the same spot become one
 * point with a count (docs/features/feature-map-overlapping-geometries.md → D).
 * Pure helpers, so grouping and colours are testable without a map.
 */

import { MAP_COLOR } from "../../shared/theme/semanticColors";

/** Decimals the geometries endpoint rounds to (~1 m); the detail page's exact
 *  coordinates are rounded the same way, so both agree on "the same spot". */
const KEY_PRECISION = 5;

export type PointProject = { id: number; groupColor?: string; points: number[][] };

export type PointCluster = {
    /** Synthetic feature id, stable for one grouping run. */
    id: number;
    coordinate: [number, number];
    /** Projects at this spot, in the order of the input, each once. */
    projectIds: number[];
    /** Group colour of the majority; a tie goes to the first project's. */
    color: string;
};

export type GroupedPoints = {
    /** Per project the points nobody else shares (projects without any are left out). */
    singles: Map<number, number[][]>;
    clusters: PointCluster[];
};

export function pointKey(coord: number[]): string {
    return `${coord[0].toFixed(KEY_PRECISION)},${coord[1].toFixed(KEY_PRECISION)}`;
}

export function majorityColor(colors: (string | undefined)[]): string {
    const counts = new Map<string, number>();
    let best: string | undefined;
    for (const color of colors) {
        const key = color ?? MAP_COLOR.default;
        const count = (counts.get(key) ?? 0) + 1;
        counts.set(key, count);
        if (best === undefined || count > (counts.get(best) ?? 0)) best = key;
    }
    return best ?? MAP_COLOR.default;
}

/** Split the projects' points into ones of their own and shared spots. */
export function groupSharedPoints(projects: PointProject[]): GroupedPoints {
    const byKey = new Map<string, { coordinate: [number, number]; projectIds: number[] }>();
    for (const project of projects) {
        for (const coord of project.points) {
            const key = pointKey(coord);
            const entry = byKey.get(key);
            if (!entry) {
                byKey.set(key, { coordinate: [coord[0], coord[1]], projectIds: [project.id] });
            } else if (!entry.projectIds.includes(project.id)) {
                entry.projectIds.push(project.id);
            }
        }
    }

    const colorOf = new Map(projects.map((p) => [p.id, p.groupColor]));
    const clusters: PointCluster[] = [];
    const shared = new Set<string>();
    for (const [key, entry] of byKey) {
        if (entry.projectIds.length < 2) continue;
        shared.add(key);
        clusters.push({
            id: clusters.length + 1,
            coordinate: entry.coordinate,
            projectIds: entry.projectIds,
            color: majorityColor(entry.projectIds.map((id) => colorOf.get(id))),
        });
    }

    const singles = new Map<number, number[][]>();
    for (const project of projects) {
        const own = project.points.filter((coord) => !shared.has(pointKey(coord)));
        if (own.length > 0) singles.set(project.id, own);
    }
    return { singles, clusters };
}

/** Relative luminance (WCAG) of a #rrggbb colour. */
function luminance(hex: string): number {
    const match = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
    if (!match) return 0;
    const channels = [0, 2, 4].map((i) => parseInt(match[1].slice(i, i + 2), 16) / 255);
    const [r, g, b] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
    const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
    return (hi + 0.05) / (lo + 0.05);
}

/** Ink or paper, whichever reads better on the counter's fill. */
export function counterTextColor(fill: string): string {
    return contrast(fill, MAP_COLOR.counterRim) >= contrast(fill, MAP_COLOR.counterTextLight)
        ? MAP_COLOR.counterRim
        : MAP_COLOR.counterTextLight;
}
