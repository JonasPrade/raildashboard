/**
 * „Stammbaum“ on the project detail page (editors and above).
 *
 * One indented tree: the superior projects above, the current project among its
 * siblings, and its whole subtree below — so an editor sees at a glance where a
 * project sits in the hierarchy before moving or merging it.
 */
import { useMemo, useState } from "react";
import { Anchor, Badge, Button, Collapse, Group, Paper, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";

import { type ProjectOption, useProjectOptions } from "../../shared/api/queries";
import { LoadingState } from "../../shared/ui/LoadingState";
import { buildFamilyTree, type FamilyNode } from "./projectFamilyTree";

type RowProps = {
    project: ProjectOption;
    depth: number;
    isCurrent?: boolean;
};

function TreeRow({ project, depth, isCurrent = false }: RowProps) {
    return (
        <Group
            gap="xs"
            wrap="nowrap"
            align="baseline"
            style={{ paddingLeft: `calc(${depth} * var(--space-4))` }}
        >
            <Text component="span" size="sm" c="var(--text-muted)" aria-hidden>
                {depth > 0 ? "└" : "•"}
            </Text>
            {isCurrent ? (
                <Text component="span" size="sm" fw={700} style={{ minWidth: 0 }}>
                    {project.name}
                </Text>
            ) : (
                <Anchor component={Link} to={`/projects/${project.id}`} size="sm" style={{ minWidth: 0 }}>
                    {project.name}
                </Anchor>
            )}
            {project.project_number && (
                <Badge size="xs" variant="outline">
                    {project.project_number}
                </Badge>
            )}
            {isCurrent && (
                <Badge size="xs" variant="light">
                    dieses Projekt
                </Badge>
            )}
        </Group>
    );
}

function Subtree({ nodes, depth }: { nodes: FamilyNode<ProjectOption>[]; depth: number }) {
    return (
        <>
            {nodes.map((node) => (
                <Stack key={node.project.id} gap={4}>
                    <TreeRow project={node.project} depth={depth} />
                    <Subtree nodes={node.children} depth={depth + 1} />
                </Stack>
            ))}
        </>
    );
}

export default function ProjectFamilyTreeSection({ projectId }: { projectId: number }) {
    const { data: options, isLoading } = useProjectOptions();
    const [open, setOpen] = useState(false);

    const tree = useMemo(
        () => (options ? buildFamilyTree(options, projectId) : null),
        [options, projectId],
    );

    if (isLoading) {
        return (
            <Paper withBorder p="var(--card-pad)">
                <LoadingState rows={3} />
            </Paper>
        );
    }
    // Drafts are not among the options and have no place in the hierarchy yet.
    if (!tree) return null;

    const selfDepth = tree.ancestors.length;
    // The current project sits among its siblings, in name order.
    const level = [...tree.siblings, tree.self].sort((a, b) => a.name.localeCompare(b.name, "de"));

    return (
        <Paper withBorder p="var(--card-pad)">
            <Stack gap="sm">
                <Group className="idt-section-head" justify="space-between" align="center">
                    <Title order={2} className="idt-title-plain">
                        Stammbaum
                    </Title>
                    <Button size="xs" variant="subtle" color="gray" onClick={() => setOpen((o) => !o)}>
                        {open ? "Ausblenden" : "Anzeigen"}
                    </Button>
                </Group>
                <Text size="sm" c="var(--text-muted)">
                    {tree.ancestors.length} darüber · {tree.siblings.length} daneben ·{" "}
                    {tree.descendantCount} darunter
                </Text>
                <Collapse in={open}>
                    <Stack gap={4}>
                        {tree.ancestors.map((ancestor, i) => (
                            <TreeRow key={ancestor.id} project={ancestor} depth={i} />
                        ))}
                        {level.map((p) =>
                            p.id === projectId ? (
                                <Stack key={p.id} gap={4}>
                                    <TreeRow project={p} depth={selfDepth} isCurrent />
                                    <Subtree nodes={tree.descendants} depth={selfDepth + 1} />
                                </Stack>
                            ) : (
                                <TreeRow key={p.id} project={p} depth={selfDepth} />
                            ),
                        )}
                    </Stack>
                </Collapse>
            </Stack>
        </Paper>
    );
}
