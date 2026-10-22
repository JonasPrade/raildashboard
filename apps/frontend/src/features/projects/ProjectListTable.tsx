import { useMemo, useState, type MouseEvent } from "react";
import { ActionIcon, Button, Group, Select, Table, Text, Tooltip, UnstyledButton } from "@mantine/core";
import { ArrowDown, ArrowUp } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import type { ProjectOverview } from "../../shared/api/queries";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import { SwatchTag } from "../../shared/ui/SwatchTag";
import PhaseBadge from "./components/progress/PhaseBadge";
import { trainCategoryLabels } from "./projectFeatureConfig";
import {
    PROJECT_SORT_LABEL,
    nextSort,
    sortProjects,
    type ProjectSort,
    type ProjectSortKey,
} from "./projectListSort";
import { usePrefetchProjectPage } from "./usePrefetchProjectPage";

type Props = {
    projects: ProjectOverview[];
    /** Rows rendered at once; the rest comes with „Weitere … anzeigen“. */
    limit: number;
    onShowMore: () => void;
    pageSize: number;
};

const ARROW_STYLE = { display: "inline-block", verticalAlign: -2, marginLeft: 6 } as const;

function SortHead({
    sortKey,
    sort,
    onSort,
    className,
}: {
    sortKey: ProjectSortKey;
    sort: ProjectSort;
    onSort: (key: ProjectSortKey) => void;
    className?: string;
}) {
    const active = sort.key === sortKey;
    const Arrow = sort.dir === "asc" ? ArrowUp : ArrowDown;
    const classes = [className, active ? "is-sorted" : null].filter(Boolean).join(" ") || undefined;
    return (
        <Table.Th
            className={classes}
            aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
            style={active ? { whiteSpace: "nowrap" } : undefined}
        >
            <UnstyledButton
                onClick={() => onSort(sortKey)}
                style={{ font: "inherit", color: "inherit", textAlign: "inherit" }}
            >
                {PROJECT_SORT_LABEL[sortKey]}
                {active && <Arrow size={14} aria-hidden style={ARROW_STYLE} />}
            </UnstyledButton>
        </Table.Th>
    );
}

/**
 * The project list of the start page (`/?view=list`) as a table after the
 * Anwendungsebene: name as heading, phase as status (card footer on a phone),
 * traffic types, length. Sortable by name, phase and length; a click on a row
 * opens the project.
 */
export function ProjectListTable({ projects, limit, onShowMore, pageSize }: Props) {
    const navigate = useNavigate();
    const prefetchProjectPage = usePrefetchProjectPage();
    const [sort, setSort] = useState<ProjectSort>({ key: null, dir: "asc" });
    const sorted = useMemo(() => sortProjects(projects, sort), [projects, sort]);
    const visible = sorted.slice(0, limit);
    const onSort = (key: ProjectSortKey) => setSort((current) => nextSort(current, key));

    const openRow = (event: MouseEvent<HTMLTableRowElement>, id: number) => {
        // Links, buttons and fields inside the row keep their own behaviour.
        if ((event.target as HTMLElement).closest("a, button, input, label")) return;
        navigate(`/projects/${id}`);
    };

    const sortControl = (
        <Group gap="xs" wrap="nowrap" style={{ width: "100%" }}>
            <Text span size="sm" c="dimmed" style={{ flex: "0 0 auto" }}>
                Sortiert nach
            </Text>
            <Select
                size="sm"
                aria-label="Sortieren nach"
                data={[
                    { value: "", label: "Reihenfolge der Gruppe" },
                    ...(Object.keys(PROJECT_SORT_LABEL) as ProjectSortKey[]).map((key) => ({
                        value: key,
                        label: PROJECT_SORT_LABEL[key],
                    })),
                ]}
                value={sort.key ?? ""}
                onChange={(value) =>
                    setSort((current) => ({ key: (value || null) as ProjectSortKey | null, dir: current.dir }))
                }
                allowDeselect={false}
                style={{ flex: 1, minWidth: 0 }}
            />
            <ActionIcon
                variant="default"
                size="lg"
                disabled={!sort.key}
                aria-label={sort.dir === "asc" ? "Absteigend sortieren" : "Aufsteigend sortieren"}
                onClick={() => setSort((current) => ({ ...current, dir: current.dir === "asc" ? "desc" : "asc" }))}
            >
                {sort.dir === "asc" ? <ArrowUp size={18} /> : <ArrowDown size={18} />}
            </ActionIcon>
        </Group>
    );

    return (
        <>
            <ResponsiveTable minWidth={720} highlightOnHover sortControl={sortControl}>
                <Table.Thead>
                    <Table.Tr>
                        <SortHead sortKey="name" sort={sort} onSort={onSort} />
                        <SortHead sortKey="phase" sort={sort} onSort={onSort} className="status" />
                        <Table.Th>Verkehrsart</Table.Th>
                        <SortHead sortKey="length" sort={sort} onSort={onSort} className="num" />
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    {visible.map((project) => {
                        const id = typeof project.id === "number" ? project.id : null;
                        const traffic = trainCategoryLabels.filter(({ key }) => Boolean(project[key]));
                        // Paused/aborted: the PAUSIERT tag says it, the name turns muted —
                        // no opacity on the row (text would fall below 4.5:1).
                        const paused = project.lifecycle_status === "PAUSIERT" || project.lifecycle_status === "ABGEBROCHEN";
                        const nameColor = paused ? "var(--text-muted)" : "var(--text-strong)";
                        return (
                            <Table.Tr
                                key={id ?? project.name}
                                style={id !== null ? { cursor: "pointer" } : undefined}
                                onClick={id !== null ? (event) => openRow(event, id) : undefined}
                                onMouseEnter={id !== null ? () => prefetchProjectPage(id) : undefined}
                            >
                                <Table.Td>
                                    {id !== null ? (
                                        <Tooltip
                                            label={project.description}
                                            disabled={!project.description}
                                            multiline
                                            w={360}
                                            withArrow
                                            openDelay={300}
                                        >
                                            <Link
                                                to={`/projects/${id}`}
                                                onFocus={() => prefetchProjectPage(id)}
                                                style={{ color: nameColor, fontWeight: 600, textDecoration: "none" }}
                                            >
                                                {project.name}
                                            </Link>
                                        </Tooltip>
                                    ) : (
                                        <Text span fw={600} style={{ color: nameColor }}>
                                            {project.name}
                                        </Text>
                                    )}
                                    {project.project_number && (
                                        <Text size="13px" c="dimmed" fw={400} style={{ display: "block" }}>
                                            Nr. {project.project_number}
                                        </Text>
                                    )}
                                </Table.Td>
                                <Table.Td data-role="status">
                                    <PhaseBadge phase={project.headline_phase} lifecycle={project.lifecycle_status} />
                                </Table.Td>
                                <Table.Td>
                                    {traffic.length > 0 ? (
                                        <Group gap={6} wrap="wrap" style={{ display: "inline-flex" }}>
                                            {traffic.map(({ key, label, color }) => (
                                                <SwatchTag key={key} color={color}>
                                                    {label}
                                                </SwatchTag>
                                            ))}
                                        </Group>
                                    ) : (
                                        <Text span c="dimmed">
                                            –
                                        </Text>
                                    )}
                                </Table.Td>
                                <Table.Td className="num">
                                    {typeof project.length === "number"
                                        ? project.length.toLocaleString("de-DE")
                                        : "–"}
                                </Table.Td>
                            </Table.Tr>
                        );
                    })}
                </Table.Tbody>
            </ResponsiveTable>
            {sorted.length > limit && (
                <Group justify="center" mt="lg">
                    <Button variant="default" onClick={onShowMore}>
                        Weitere {Math.min(pageSize, sorted.length - limit)} von {sorted.length - limit} Projekten anzeigen
                    </Button>
                </Group>
            )}
        </>
    );
}

export default ProjectListTable;
