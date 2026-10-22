/**
 * Family tree of a project („Stammbaum“): the chain of superior projects above
 * it, the projects beside it (same parent) and every project below it.
 *
 * Built from the slim project options (`/projects/options`, drafts excluded) —
 * the hierarchy only needs `id` and `superior_project_id`, not the full records.
 */

export interface FamilyProject {
    id: number;
    name: string;
    project_number?: string | null;
    superior_project_id?: number | null;
}

export interface FamilyNode<P extends FamilyProject = FamilyProject> {
    project: P;
    children: FamilyNode<P>[];
}

export interface FamilyTree<P extends FamilyProject = FamilyProject> {
    self: P;
    /** Superior projects, the topmost first and the direct parent last. */
    ancestors: P[];
    /** Projects with the same parent, by name. Empty for a top-level project. */
    siblings: P[];
    /** Direct children of the project, each with its own subtree. */
    descendants: FamilyNode<P>[];
    /** Number of projects in `descendants`, at every depth. */
    descendantCount: number;
}

const byName = (a: FamilyProject, b: FamilyProject) => a.name.localeCompare(b.name, "de");

/**
 * Returns the family tree of *projectId*, or null when it is not among *projects*.
 *
 * A corrupt cyclic chain cannot hang the page: every walk stops at a project it
 * has already visited.
 */
export function buildFamilyTree<P extends FamilyProject>(
    projects: P[],
    projectId: number,
): FamilyTree<P> | null {
    const byId = new Map(projects.map((p) => [p.id, p]));
    const self = byId.get(projectId);
    if (!self) return null;

    const childrenOf = new Map<number, P[]>();
    for (const p of projects) {
        if (p.superior_project_id == null) continue;
        const list = childrenOf.get(p.superior_project_id) ?? [];
        list.push(p);
        childrenOf.set(p.superior_project_id, list);
    }
    for (const list of childrenOf.values()) list.sort(byName);

    const ancestors: P[] = [];
    const seen = new Set<number>([self.id]);
    let parentId = self.superior_project_id;
    while (parentId != null && !seen.has(parentId)) {
        const parent = byId.get(parentId);
        if (!parent) break;
        seen.add(parent.id);
        ancestors.unshift(parent);
        parentId = parent.superior_project_id;
    }

    const directParent = ancestors.at(-1);
    const siblings = directParent
        ? (childrenOf.get(directParent.id) ?? []).filter((p) => p.id !== self.id)
        : [];

    const visited = new Set<number>([self.id, ...ancestors.map((a) => a.id)]);
    let descendantCount = 0;
    const subtree = (id: number): FamilyNode<P>[] =>
        (childrenOf.get(id) ?? [])
            .filter((child) => !visited.has(child.id))
            .map((child) => {
                visited.add(child.id);
                descendantCount += 1;
                return { project: child, children: subtree(child.id) };
            });
    const descendants = subtree(self.id);

    return { self, ancestors, siblings, descendants, descendantCount };
}
