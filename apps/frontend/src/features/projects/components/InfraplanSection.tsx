import { useMemo } from "react";
import { Alert, Anchor, Badge, Group, Paper, Stack, Table, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";
import { useProjectInfraplan, type InfraplanProjectEntry } from "../../../shared/api/queries";
import { ResponsiveTable } from "../../../shared/ui/ResponsiveTable";
import Footnotes from "../../infraplan/Footnotes";
import { PARL_LABEL, SECTION_SHORT, entryCost, entryDeltas, formatMio } from "../../infraplan/infraplanFormat";
import { LoadingState } from "../../../shared/ui/LoadingState";

// ---------------------------------------------------------------------------
// Infraplan on the project page (docs/features/feature-infraplan-import.md →
// „Anzeige“): one row per year and entry, change hints from the second year
// on, and a note when the project dropped out of the newest year.
// ---------------------------------------------------------------------------

function sortEntries(entries: InfraplanProjectEntry[]): InfraplanProjectEntry[] {
    return [...entries].sort(
        (a, b) => b.report_year - a.report_year || a.section.localeCompare(b.section) || a.lfd_nr - b.lfd_nr,
    );
}

export default function InfraplanSection({ projectId }: { projectId: number }) {
    const { data, isLoading } = useProjectInfraplan(projectId);
    const entries = useMemo(() => sortEntries(data?.entries ?? []), [data]);
    const deltas = useMemo(() => entryDeltas(entries), [entries]);

    if (isLoading) return <LoadingState rows={3} />;
    if (!data || entries.length === 0) return null;

    return (
        <Paper withBorder p="var(--card-pad)">
            <Stack gap="md">
                <Group justify="space-between" wrap="wrap">
                    <Title order={4}>Infraplan</Title>
                    <Anchor component={Link} to="/infraplan" size="sm">Infraplan-Übersicht →</Anchor>
                </Group>
                {data.missing_in_latest && data.latest_year != null && (
                    <Alert color="orange" variant="light">
                        Nicht mehr im Infraplan {data.latest_year} enthalten.
                    </Alert>
                )}
                <ResponsiveTable minWidth={880} striped verticalSpacing="xs" fz="sm">
                    <Table.Thead>
                        <Table.Tr>
                            <Table.Th>Jahrgang</Table.Th>
                            <Table.Th>Abschnitt</Table.Th>
                            <Table.Th>Realisierungsstand</Table.Th>
                            <Table.Th>Inbetriebnahme gepl.</Table.Th>
                            <Table.Th ta="right">Kosten Mio. €</Table.Th>
                            <Table.Th>Befassung</Table.Th>
                            <Table.Th>Veränderung</Table.Th>
                        </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                        {entries.map((e) => {
                            const cost = entryCost(e);
                            const hints = deltas.get(e.id) ?? [];
                            return (
                                <Table.Tr key={`${e.id}-${e.project_id}`}>
                                    <Table.Td fw={600}>{e.report_year}</Table.Td>
                                    <Table.Td style={{ maxWidth: 280 }}>
                                        <Text size="sm">
                                            {SECTION_SHORT[e.section] ?? e.section_title} Nr. {e.lfd_nr}
                                            {e.primary_number ? ` · ${e.primary_number}` : ""}
                                        </Text>
                                        <Text size="xs" c="dimmed">
                                            {e.massnahme ?? e.bezeichnung ?? ""}
                                            <Footnotes footnotes={e.footnotes} />
                                        </Text>
                                        {e.project_id !== projectId && e.project_name && (
                                            <Anchor component={Link} to={`/projects/${e.project_id}`} size="xs">
                                                {e.project_name}
                                            </Anchor>
                                        )}
                                    </Table.Td>
                                    <Table.Td style={{ maxWidth: 200 }}>{e.state_raw ?? "–"}</Table.Td>
                                    <Table.Td style={{ whiteSpace: "nowrap" }}>{e.ibn_raw ?? "–"}</Table.Td>
                                    <Table.Td ta="right" style={{ whiteSpace: "nowrap" }}>
                                        {cost !== null ? (
                                            <>
                                                {formatMio(cost)}
                                                <Text span size="xs" c="dimmed">
                                                    {" "}
                                                    {e.cost_kind === "GESAMTKOSTEN" ? "GK" : "GWU"}
                                                    {e.cost_mio == null ? " (Verweis)" : ""}
                                                </Text>
                                            </>
                                        ) : (
                                            (e.cost_ref_raw ?? "–")
                                        )}
                                    </Table.Td>
                                    <Table.Td>
                                        {e.parl_state ? (PARL_LABEL[e.parl_state] ?? e.parl_state) : (e.parl_raw ?? "–")}
                                    </Table.Td>
                                    <Table.Td>
                                        <Group gap={4} wrap="wrap">
                                            {hints.map((h) => (
                                                <Badge key={h} size="sm" variant="outline">
                                                    {h}
                                                </Badge>
                                            ))}
                                        </Group>
                                    </Table.Td>
                                </Table.Tr>
                            );
                        })}
                    </Table.Tbody>
                </ResponsiveTable>
                <Text size="xs" c="dimmed">
                    GWU = Gesamtwertumfang, GK = Gesamtkosten (GVFG: Länderangabe). Veränderungen gegenüber dem
                    vorherigen Jahrgang derselben Maßnahme.
                </Text>
            </Stack>
        </Paper>
    );
}
