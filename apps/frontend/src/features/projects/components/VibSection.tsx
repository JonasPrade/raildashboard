import { useState } from "react";
import {
    Badge,
    Card,
    Collapse,
    Group,
    Loader,
    Paper,
    Stack,
    Table,
    Tabs,
    Text,
    Title,
} from "@mantine/core";
import { type VibEntryForProject, useProjectVibEntries } from "../../../shared/api/queries";

const CATEGORY_COLORS: Record<string, string> = {
    laufend: "blue",
    neu: "green",
    potentiell: "yellow",
    abgeschlossen: "gray",
};

function VibTabContent({ entry }: { entry: VibEntryForProject }) {
    const [rawExpanded, setRawExpanded] = useState(false);
    const [pfaExpanded, setPfaExpanded] = useState(false);

    return (
        <Stack gap="md">
            <Group gap="sm">
                <Badge size="sm" color={CATEGORY_COLORS[entry.category] ?? "gray"} variant="light">
                    {entry.category}
                </Badge>
                {entry.vib_section && (
                    <Text size="xs" c="dimmed" ff="monospace">
                        {entry.vib_section}
                    </Text>
                )}
                {entry.drucksache_nr && (
                    <Text size="xs" c="dimmed">
                        Drucksache {entry.drucksache_nr}
                    </Text>
                )}
                {entry.ai_extracted && (
                    <Badge size="xs" color="violet" variant="dot">
                        KI-extrahiert
                    </Badge>
                )}
                {entry.status_planung && (
                    <Badge size="sm" color="orange" variant="light">Planung</Badge>
                )}
                {entry.status_bau && (
                    <Badge size="sm" color="cyan" variant="light">Bau</Badge>
                )}
                {entry.status_abgeschlossen && (
                    <Badge size="sm" color="green" variant="light">Abgeschlossen</Badge>
                )}
            </Group>

            {/* Projektkenndaten */}
            {(entry.strecklaenge_km !== null || entry.gesamtkosten_mio_eur !== null || entry.entwurfsgeschwindigkeit) && (
                <Group gap="lg">
                    {entry.strecklaenge_km !== null && (
                        <Text size="sm">
                            <b>Länge:</b> {entry.strecklaenge_km} km
                        </Text>
                    )}
                    {entry.gesamtkosten_mio_eur !== null && (
                        <Text size="sm">
                            <b>Gesamtkosten:</b> {entry.gesamtkosten_mio_eur} Mio. €
                        </Text>
                    )}
                    {entry.entwurfsgeschwindigkeit && (
                        <Text size="sm">
                            <b>Vmax:</b> {entry.entwurfsgeschwindigkeit} km/h
                        </Text>
                    )}
                </Group>
            )}

            {entry.planungsstand && (
                <div>
                    <Text size="sm" fw={600} mb={4}>
                        Planungsstand
                    </Text>
                    <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                        {entry.planungsstand}
                    </Text>
                </div>
            )}

            {/* Bauaktivitäten */}
            {entry.bauaktivitaeten && (
                <div>
                    <Text size="sm" fw={600} mb={4}>
                        Bauaktivitäten {entry.year}
                    </Text>
                    <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                        {entry.bauaktivitaeten}
                    </Text>
                </div>
            )}

            {/* Teilinbetriebnahmen */}
            {entry.teilinbetriebnahmen && (
                <div>
                    <Text size="sm" fw={600} mb={4}>
                        Teilinbetriebnahmen {entry.year}
                    </Text>
                    <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                        {entry.teilinbetriebnahmen}
                    </Text>
                </div>
            )}

            {/* PFA-Tabelle */}
            {entry.pfa_entries.length > 0 && (
                <div>
                    <Group gap="xs" mb={4} style={{ cursor: "pointer" }} onClick={() => setPfaExpanded((v) => !v)}>
                        <Text size="sm" fw={600}>
                            PFA-Tabelle ({entry.pfa_entries.length} Einträge)
                        </Text>
                        <Text size="xs" c="dimmed">
                            {pfaExpanded ? "▲ ausblenden" : "▼ anzeigen"}
                        </Text>
                    </Group>
                    <Collapse in={pfaExpanded}>
                        <Paper withBorder p={0} style={{ overflow: "auto" }}>
                            <Table withTableBorder withColumnBorders fz="xs" style={{ fontSize: 11 }}>
                                <Table.Thead>
                                    <Table.Tr>
                                        <Table.Th>Nr.</Table.Th>
                                        <Table.Th>Örtlichkeit</Table.Th>
                                        <Table.Th>Abschluss FinVe</Table.Th>
                                        <Table.Th>PFB</Table.Th>
                                        <Table.Th>Baubeginn</Table.Th>
                                        <Table.Th>IBM</Table.Th>
                                    </Table.Tr>
                                </Table.Thead>
                                <Table.Tbody>
                                    {entry.pfa_entries.map((pfa) => (
                                        <Table.Tr key={pfa.id}>
                                            <Table.Td>
                                                {pfa.abschnitt_label ? `${pfa.abschnitt_label} / ` : ""}
                                                {pfa.nr_pfa}
                                            </Table.Td>
                                            <Table.Td>{pfa.oertlichkeit ?? "–"}</Table.Td>
                                            <Table.Td>{pfa.abschluss_finve ?? "–"}</Table.Td>
                                            <Table.Td>{pfa.datum_pfb ?? "–"}</Table.Td>
                                            <Table.Td>{pfa.baubeginn ?? "–"}</Table.Td>
                                            <Table.Td>{pfa.inbetriebnahme ?? "–"}</Table.Td>
                                        </Table.Tr>
                                    ))}
                                </Table.Tbody>
                            </Table>
                        </Paper>
                    </Collapse>
                </div>
            )}

            {/* Volltext */}
            {entry.raw_text && (
                <div>
                    <Group gap="xs" mb={4} style={{ cursor: "pointer" }} onClick={() => setRawExpanded((v) => !v)}>
                        <Text size="sm" fw={600}>
                            Volltext
                        </Text>
                        <Text size="xs" c="dimmed">
                            {rawExpanded ? "▲ ausblenden" : "▼ anzeigen"}
                        </Text>
                    </Group>
                    <Collapse in={rawExpanded}>
                        <Text size="xs" c="dimmed" style={{ whiteSpace: "pre-wrap" }}>
                            {entry.raw_text}
                        </Text>
                    </Collapse>
                </div>
            )}
        </Stack>
    );
}

export default function VibSection({ projectId }: { projectId: number }) {
    const { data: entries, isLoading } = useProjectVibEntries(projectId);

    if (isLoading) {
        return (
            <Card withBorder radius="md" padding="lg" shadow="xs">
                <Stack gap="sm">
                    <Title order={4}>Verkehrsinvestitionsberichte</Title>
                    <Group justify="center">
                        <Loader size="sm" />
                    </Group>
                </Stack>
            </Card>
        );
    }

    if (!entries || entries.length === 0) {
        return null;
    }

    // Group by year (entries are already sorted newest first)
    const years = [...new Set(entries.map((e) => e.year))];

    return (
        <Card withBorder radius="md" padding="lg" shadow="xs">
            <Stack gap="md">
                <Title order={4}>Verkehrsinvestitionsberichte</Title>
                <Tabs defaultValue={String(years[0])}>
                    <Tabs.List>
                        {years.map((year) => (
                            <Tabs.Tab key={year} value={String(year)}>
                                {year}
                            </Tabs.Tab>
                        ))}
                    </Tabs.List>
                    {years.map((year) => {
                        const yearEntries = entries.filter((e) => e.year === year);
                        return (
                            <Tabs.Panel key={year} value={String(year)} pt="md">
                                <Stack gap="xl">
                                    {yearEntries.map((entry) => (
                                        <VibTabContent key={entry.id} entry={entry} />
                                    ))}
                                </Stack>
                            </Tabs.Panel>
                        );
                    })}
                </Tabs>
            </Stack>
        </Card>
    );
}
