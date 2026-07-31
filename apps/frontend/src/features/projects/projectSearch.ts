/**
 * Pure helpers behind ProjectSearchSelect — kept out of the component so the
 * matching/ranking behaviour can be unit-tested.
 */

export type SearchableProject = {
    id?: number | null;
    name?: string | null;
    project_number?: string | null;
    superior_project_id?: number | null;
};

/**
 * Fold a string into a comparable form: diacritics stripped (Lübeck → lubeck),
 * ß → ss, every non-alphanumeric run (hyphens, en dashes, slashes, dots) turned
 * into a single space. Lets "hamburg-lubeck" find "ABS Hamburg–Lübeck".
 */
export function normalizeSearchText(value: string | null | undefined): string {
    return (value ?? "")
        .normalize("NFD")
        .replace(/[̀-ͯ]/g, "")
        .toLowerCase()
        .replace(/ß/g, "ss")
        .replace(/[^a-z0-9]+/g, " ")
        .trim();
}

/**
 * Normalised name/number of a project, cached per object.
 *
 * ``normalizeSearchText`` runs four regex passes; without this cache every
 * keystroke re-normalised every project twice over (once to filter, once to
 * rank). React Query hands out stable project objects, so the entries survive
 * across keystrokes and the WeakMap releases them when the list is replaced.
 */
const normalizedCache = new WeakMap<object, { name: string; number: string }>();

function normalized(project: SearchableProject): { name: string; number: string } {
    const cached = normalizedCache.get(project);
    if (cached) return cached;
    const entry = {
        name: normalizeSearchText(project.name),
        number: normalizeSearchText(project.project_number),
    };
    normalizedCache.set(project, entry);
    return entry;
}

/** Rank of a project for `normalizedQuery` — lower is better. */
function rank(project: SearchableProject, normalizedQuery: string): number {
    if (normalizedQuery === "") return 0;
    const { name, number } = normalized(project);

    if (name === normalizedQuery || number === normalizedQuery) return 0;
    if (name.startsWith(normalizedQuery) || number.startsWith(normalizedQuery)) return 1;
    if (name.includes(` ${normalizedQuery}`)) return 2; // hit at a word boundary
    if (name.includes(normalizedQuery)) return 3;
    return 4; // matched only through individually scattered tokens
}

/**
 * All ids in the subtree below (and including) `rootId`.
 *
 * Used to keep a project from being assigned one of its own descendants as
 * superior project, which would create a cycle. Guards against pre-existing
 * cycles in the data by never visiting an id twice.
 */
export function collectSubtreeIds(
    projects: readonly SearchableProject[],
    rootId: number | null | undefined,
): Set<number> {
    const ids = new Set<number>();
    if (typeof rootId !== "number") return ids;

    const childrenByParent = new Map<number, number[]>();
    for (const project of projects) {
        const parentId = project.superior_project_id;
        if (typeof parentId !== "number" || typeof project.id !== "number") continue;
        const siblings = childrenByParent.get(parentId);
        if (siblings) siblings.push(project.id);
        else childrenByParent.set(parentId, [project.id]);
    }

    const queue = [rootId];
    while (queue.length > 0) {
        const current = queue.pop() as number;
        if (ids.has(current)) continue;
        ids.add(current);
        queue.push(...(childrenByParent.get(current) ?? []));
    }
    return ids;
}

export type SearchProjectsOptions = {
    /** Ids that must never appear in the result (e.g. the project's own subtree). */
    excludeIds?: ReadonlySet<number>;
};

/**
 * Projects matching `query`, best match first.
 *
 * A project matches when *every* whitespace-separated token of the query occurs
 * in its name or project number, so word order does not matter
 * ("lubeck hamburg" still finds "ABS Hamburg–Lübeck"). An empty query returns
 * every (non-excluded) project sorted by name.
 */
export function searchProjects<T extends SearchableProject>(
    projects: readonly T[],
    query: string,
    { excludeIds }: SearchProjectsOptions = {},
): T[] {
    const normalizedQuery = normalizeSearchText(query);
    const tokens = normalizedQuery.split(" ").filter(Boolean);

    const matches = projects.filter((project) => {
        if (typeof project.id !== "number") return false;
        if (excludeIds?.has(project.id)) return false;
        if (tokens.length === 0) return true;
        const { name, number } = normalized(project);
        const haystack = `${name} ${number}`;
        return tokens.every((token) => haystack.includes(token));
    });

    // Rank once per match, then sort on the precomputed value — a comparator
    // that called rank() would recompute it O(n log n) times.
    return matches
        .map((project) => ({ project, rank: rank(project, normalizedQuery) }))
        .sort(
            (a, b) =>
                a.rank - b.rank ||
                (a.project.name ?? "").length - (b.project.name ?? "").length ||
                (a.project.name ?? "").localeCompare(b.project.name ?? "", "de"),
        )
        .map((entry) => entry.project);
}
