import { useState } from "react";
import { Equal, Minus, Plus, type LucideIcon } from "lucide-react";
import { Anchor, Badge, Group, SegmentedControl, SimpleGrid, Stack, Text } from "@mantine/core";
import { Link } from "react-router-dom";

import { type ProjectRef, type SammelYear, useSammelFinveYears } from "../../../shared/api/queries";
import { ARCHIVE_TONE, SAMMEL_DIFF_COLOR } from "../../../shared/theme/semanticColors";
import { ErrorState } from "../../../shared/ui/ErrorState";
import { LoadingState } from "../../../shared/ui/LoadingState";
import ProjectHoverCard from "../../projects/ProjectHoverCard";

type ColumnKey = keyof typeof SAMMEL_DIFF_COLOR;

const COLUMNS: { key: ColumnKey; label: string; icon: LucideIcon }[] = [
    { key: "added", label: "Neu aufgenommen", icon: Plus },
    { key: "kept", label: "Weiterhin enthalten", icon: Equal },
    { key: "removed", label: "Nicht mehr enthalten", icon: Minus },
];

function ProjectColumn({
    label,
    icon: Icon,
    color,
    projects,
    empty,
}: {
    label: string;
    icon: LucideIcon;
    color: string;
    projects: ProjectRef[];
    empty: string;
}) {
    return (
        <Stack gap="xs" style={{ borderTop: `4px solid ${color}`, paddingTop: "var(--mantine-spacing-xs)" }}>
            <Group gap={6} wrap="nowrap">
                <Icon size={16} aria-hidden />
                <Text size="sm" fw={600}>
                    {label}
                </Text>
                <Text size="sm" c="dimmed" className="idt-tnum">
                    {projects.length}
                </Text>
            </Group>
            {projects.length === 0 && (
                <Text size="sm" c="dimmed">
                    {empty}
                </Text>
            )}
            {projects.map((p) => (
                <Group key={p.id} gap="xs" wrap="nowrap" style={{ minWidth: 0 }}>
                    <ProjectHoverCard projectId={p.id}>
                        <Anchor component={Link} to={`/projects/${p.id}`} size="sm" lineClamp={2}>
                            {p.name}
                        </Anchor>
                    </ProjectHoverCard>
                    {p.is_archived && (
                        <Badge variant="outline" color={ARCHIVE_TONE} size="xs">
                            Archiviert
                        </Badge>
                    )}
                </Group>
            ))}
        </Stack>
    );
}

/**
 * Year comparison of a Sammel-FinVe: per Haushalt edition which projects
 * entered, which stay and which dropped out against the previous edition. The
 * agreement's conclusion year says nothing about a single project — its list is
 * rewritten every year.
 */
export function SammelYearsComparison({ finveId }: { finveId: number }) {
    const { data, isLoading, isError, refetch } = useSammelFinveYears(finveId);
    const years = data?.years ?? [];
    // null → the newest edition.
    const [selected, setSelected] = useState<number | null>(null);

    if (isLoading) return <LoadingState rows={3} />;
    if (isError) {
        return <ErrorState onRetry={() => void refetch()}>Jahresvergleich konnte nicht geladen werden.</ErrorState>;
    }
    if (years.length === 0) {
        return (
            <Text size="sm" c="dimmed">
                Noch kein Haushaltsjahrgang mit Projektzuordnungen eingelesen.
            </Text>
        );
    }

    const current: SammelYear = years.find((y) => y.year === selected) ?? years[years.length - 1];
    const isFirst = current.previous_year == null;

    return (
        <Stack gap="md">
            <Group gap="sm" wrap="wrap" align="center">
                <Text size="sm" c="dimmed">
                    Haushalt
                </Text>
                <SegmentedControl
                    size="xs"
                    value={String(current.year)}
                    onChange={(v) => setSelected(Number(v))}
                    data={years.map((y) => ({ value: String(y.year), label: String(y.year) }))}
                />
                <Text size="sm" c="dimmed">
                    {isFirst
                        ? "erster eingelesener Jahrgang – kein Vorjahr zum Vergleich"
                        : `im Vergleich zu ${current.previous_year}`}
                </Text>
            </Group>
            <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg">
                {COLUMNS.map((col) => (
                    <ProjectColumn
                        key={col.key}
                        label={isFirst && col.key === "kept" ? "Enthalten" : col.label}
                        icon={col.icon}
                        color={SAMMEL_DIFF_COLOR[col.key]}
                        projects={current[col.key] ?? []}
                        empty={isFirst && col.key !== "kept" ? "Kein Vorjahr eingelesen." : "Keine."}
                    />
                ))}
            </SimpleGrid>
        </Stack>
    );
}
