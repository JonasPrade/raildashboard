/**
 * Sorting of the project list (`/?view=list`), kept out of the component so it
 * can be unit-tested. Without a sort key the list keeps the group's order.
 */
import { MAIN_PHASES } from "./components/progress/phaseMeta";

export type ProjectSortKey = "name" | "phase" | "length";
export type SortDirection = "asc" | "desc";
export type ProjectSort = { key: ProjectSortKey | null; dir: SortDirection };

export const PROJECT_SORT_LABEL: Record<ProjectSortKey, string> = {
    name: "Projekt",
    phase: "Phase",
    length: "Länge (km)",
};

type Sortable = {
    name: string;
    headline_phase?: string | null;
    length?: number | null;
};

const phaseRank = (phase: string | null | undefined): number | null => {
    const index = phase ? (MAIN_PHASES as string[]).indexOf(phase) : -1;
    return index >= 0 ? index : null;
};

/** Clicking a head: same column flips the direction, another column starts ascending. */
export function nextSort(current: ProjectSort, key: ProjectSortKey): ProjectSort {
    if (current.key === key) return { key, dir: current.dir === "asc" ? "desc" : "asc" };
    return { key, dir: "asc" };
}

/**
 * Returns a sorted copy. Projects without a value (no phase, no length) always
 * go last, whatever the direction; ties keep the incoming order.
 */
export function sortProjects<T extends Sortable>(projects: readonly T[], sort: ProjectSort): T[] {
    const { key, dir } = sort;
    if (!key) return [...projects];
    const sign = dir === "asc" ? 1 : -1;
    const value = (p: T): string | number | null => {
        if (key === "name") return p.name ?? "";
        if (key === "phase") return phaseRank(p.headline_phase);
        return typeof p.length === "number" && Number.isFinite(p.length) ? p.length : null;
    };
    return projects
        .map((project, index) => ({ project, index, v: value(project) }))
        .sort((a, b) => {
            if (a.v === null || b.v === null) {
                if (a.v === b.v) return a.index - b.index;
                return a.v === null ? 1 : -1;
            }
            const cmp =
                typeof a.v === "string" && typeof b.v === "string"
                    ? a.v.localeCompare(b.v, "de", { sensitivity: "base", numeric: true })
                    : (a.v as number) - (b.v as number);
            return cmp !== 0 ? cmp * sign : a.index - b.index;
        })
        .map(({ project }) => project);
}
