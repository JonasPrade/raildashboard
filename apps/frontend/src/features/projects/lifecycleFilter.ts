/**
 * Pure helpers behind the "Beendete Projekte einblenden" switch on the map/list
 * page (`/`). Replaced and aborted projects are hidden unless `?beendet=1`
 * (docs/features/feature-project-replacement.md, W2); paused ones stay visible.
 */

/** URL search param; `1` shows ended projects, absent hides them. */
export const ENDED_PARAM = "beendet";

/** Lifecycle states of projects that no longer run. */
export const ENDED_LIFECYCLES: ReadonlySet<string> = new Set(["ABGEBROCHEN", "ERSETZT"]);

export function parseShowEnded(raw: string | null | undefined): boolean {
    return raw === "1";
}

export type LifecycleFilterable = { lifecycle_status?: string | null };

export function isEnded(project: LifecycleFilterable): boolean {
    return ENDED_LIFECYCLES.has(project.lifecycle_status ?? "");
}

/**
 * Drop ended projects unless `showEnded`. Returns the input unchanged (same
 * array) when nothing is dropped, so memoised consumers do not re-render.
 */
export function filterEndedProjects<T extends LifecycleFilterable>(projects: T[], showEnded: boolean): T[] {
    if (showEnded) return projects;
    const kept = projects.filter((project) => !isEnded(project));
    return kept.length === projects.length ? projects : kept;
}
