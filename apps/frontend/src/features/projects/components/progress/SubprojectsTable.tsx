import { useMemo, useState } from "react";
import { Anchor, Badge, Group, Stack, Table, Text, TextInput } from "@mantine/core";
import { IconSearch } from "@tabler/icons-react";
import { Link } from "react-router-dom";

import type { ProgressChild } from "../../../../shared/api/queries";
import {
    LIFECYCLE_LABEL,
    MAIN_PHASES,
    MAIN_PHASE_COLOR,
    MAIN_PHASE_LABEL,
    UNKNOWN_LABEL,
    type LifecycleStatus,
    type MainPhase,
    groupChildrenByPhase,
} from "./phaseMeta";

function phaseBadge(child: ProgressChild) {
    if (child.is_known === false) {
        return (
            <Badge variant="outline" color="gray">
                {UNKNOWN_LABEL}
            </Badge>
        );
    }
    // A nested superior carries a span over its own subprojects, not one phase.
    const lo = child.span_min_phase as MainPhase | null;
    const hi = child.span_max_phase as MainPhase | null;
    if (child.is_superior && lo && hi && lo !== hi) {
        return (
            <Group gap={4} wrap="nowrap">
                <Badge variant="light" color={MAIN_PHASE_COLOR[lo] ?? "gray"}>
                    {MAIN_PHASE_LABEL[lo] ?? lo}
                </Badge>
                <Text size="xs" c="dimmed">
                    –
                </Text>
                <Badge variant="light" color={MAIN_PHASE_COLOR[hi] ?? "gray"}>
                    {MAIN_PHASE_LABEL[hi] ?? hi}
                </Badge>
            </Group>
        );
    }
    const phase = child.effective_phase as MainPhase;
    return (
        <Badge variant="light" color={MAIN_PHASE_COLOR[phase] ?? "gray"}>
            {MAIN_PHASE_LABEL[phase] ?? phase}
        </Badge>
    );
}

export default function SubprojectsTable({ children }: { children: ProgressChild[] }) {
    const [query, setQuery] = useState("");

    const { byPhase, unknown } = useMemo(() => groupChildrenByPhase(children), [children]);

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (!q) return children;
        return children.filter((c) => c.name.toLowerCase().includes(q));
    }, [children, query]);

    return (
        <Stack gap="sm">
            <Group justify="space-between" align="center" wrap="wrap">
                <Text size="sm" fw={700}>
                    Unterprojekte ({children.length})
                </Text>
                {/* Status distribution — makes differing statuses immediately visible. */}
                <Group gap={6}>
                    {MAIN_PHASES.map((phase) => {
                        const count = byPhase[phase]?.length ?? 0;
                        if (count === 0) return null;
                        return (
                            <Badge key={phase} variant="light" color={MAIN_PHASE_COLOR[phase]}>
                                {count}× {MAIN_PHASE_LABEL[phase]}
                            </Badge>
                        );
                    })}
                    {unknown.length > 0 && (
                        <Badge variant="outline" color="gray">
                            {unknown.length}× {UNKNOWN_LABEL}
                        </Badge>
                    )}
                </Group>
            </Group>

            <TextInput
                size="xs"
                placeholder="Unterprojekt suchen …"
                leftSection={<IconSearch size={14} />}
                value={query}
                onChange={(e) => setQuery(e.currentTarget.value)}
                w={260}
            />

            <Table striped withTableBorder highlightOnHover>
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th>Projekt</Table.Th>
                        <Table.Th>Planungsstand</Table.Th>
                        <Table.Th>Lebenszyklus</Table.Th>
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    {filtered.map((child) => (
                        <Table.Tr key={child.project_id}>
                            <Table.Td>
                                <Group gap={6} wrap="nowrap">
                                    <Anchor component={Link} to={`/projects/${child.project_id}`} size="sm">
                                        {child.name}
                                    </Anchor>
                                    {child.is_superior && (
                                        <Badge size="xs" variant="outline" color="gray" title="Hat eigene Unterprojekte">
                                            Gruppe
                                        </Badge>
                                    )}
                                </Group>
                            </Table.Td>
                            <Table.Td>{phaseBadge(child)}</Table.Td>
                            <Table.Td>
                                {child.lifecycle_status !== "AKTIV" ? (
                                    <Badge
                                        size="sm"
                                        color={child.lifecycle_status === "ABGEBROCHEN" ? "red" : "orange"}
                                    >
                                        {LIFECYCLE_LABEL[child.lifecycle_status as LifecycleStatus]}
                                    </Badge>
                                ) : (
                                    <Text size="xs" c="dimmed">
                                        aktiv
                                    </Text>
                                )}
                            </Table.Td>
                        </Table.Tr>
                    ))}
                    {filtered.length === 0 && (
                        <Table.Tr>
                            <Table.Td colSpan={3}>
                                <Text size="sm" c="dimmed">
                                    Kein Unterprojekt gefunden.
                                </Text>
                            </Table.Td>
                        </Table.Tr>
                    )}
                </Table.Tbody>
            </Table>
        </Stack>
    );
}
