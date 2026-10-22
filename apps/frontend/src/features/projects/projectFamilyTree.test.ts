import { describe, expect, it } from "vitest";

import { buildFamilyTree, type FamilyNode, type FamilyProject } from "./projectFamilyTree";

const PROJECTS: FamilyProject[] = [
    { id: 1, name: "ABS Hamburg–Lübeck–Puttgarden" },
    { id: 2, name: "Lübeck–Puttgarden", superior_project_id: 1 },
    { id: 3, name: "Hamburg–Lübeck", superior_project_id: 1 },
    { id: 4, name: "Fehmarnsundquerung", superior_project_id: 2 },
    { id: 5, name: "Bahnhof Puttgarden", superior_project_id: 2 },
    { id: 6, name: "Sundbrücke Ersatzneubau", superior_project_id: 4 },
    { id: 7, name: "NBS Hannover–Bielefeld" },
];

const names = (projects: FamilyProject[]) => projects.map((p) => p.name);
const tree = (nodes: FamilyNode[]): unknown =>
    nodes.map((n) => (n.children.length ? [n.project.name, tree(n.children)] : n.project.name));

describe("buildFamilyTree", () => {
    it("lists superior projects above, siblings beside and the subtree below", () => {
        const result = buildFamilyTree(PROJECTS, 2)!;
        expect(names(result.ancestors)).toEqual(["ABS Hamburg–Lübeck–Puttgarden"]);
        expect(names(result.siblings)).toEqual(["Hamburg–Lübeck"]);
        expect(tree(result.descendants)).toEqual([
            "Bahnhof Puttgarden",
            ["Fehmarnsundquerung", ["Sundbrücke Ersatzneubau"]],
        ]);
        expect(result.descendantCount).toBe(3);
    });

    it("orders the ancestor chain from the top down", () => {
        const result = buildFamilyTree(PROJECTS, 6)!;
        expect(names(result.ancestors)).toEqual([
            "ABS Hamburg–Lübeck–Puttgarden",
            "Lübeck–Puttgarden",
            "Fehmarnsundquerung",
        ]);
        expect(result.siblings).toEqual([]);
        expect(result.descendants).toEqual([]);
    });

    it("has no siblings for a top-level project", () => {
        const result = buildFamilyTree(PROJECTS, 7)!;
        expect(result.ancestors).toEqual([]);
        expect(result.siblings).toEqual([]);
        expect(result.descendantCount).toBe(0);
    });

    it("returns null for an unknown project", () => {
        expect(buildFamilyTree(PROJECTS, 99)).toBeNull();
    });

    it("survives a cyclic hierarchy", () => {
        const cyclic: FamilyProject[] = [
            { id: 1, name: "A", superior_project_id: 2 },
            { id: 2, name: "B", superior_project_id: 1 },
        ];
        const result = buildFamilyTree(cyclic, 1)!;
        expect(names(result.ancestors)).toEqual(["B"]);
        expect(result.descendants).toEqual([]);
    });
});
