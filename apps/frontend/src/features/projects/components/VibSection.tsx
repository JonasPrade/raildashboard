import { useState } from "react";
import {
    Button,
    Collapse,
    Group,
    Loader,
    Stack,
    Table,
    Tabs,
    Text,
    Title,
} from "@mantine/core";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { type VibEntryForProject, type VibEntrySchema, useProjectVibEntries } from "../../../shared/api/queries";
import { ChronicleCard, ChronicleDataChip } from "../../../components/chronicle";
import { useAuth } from "../../../lib/auth";
import VibEntryEditDrawer from "../../vib-import/VibEntryEditDrawer";

function toVibEntrySchema(entry: VibEntryForProject): VibEntrySchema {
    return {
        id: entry.id,
        vib_report_id: 0,
        vib_section: entry.vib_section,
        vib_lfd_nr: null,
        vib_name_raw: entry.vib_name_raw,
        category: entry.category,
        raw_text: entry.raw_text,
        bauaktivitaeten: entry.bauaktivitaeten,
        teilinbetriebnahmen: entry.teilinbetriebnahmen,
        verkehrliche_zielsetzung: entry.verkehrliche_zielsetzung,
        durchgefuehrte_massnahmen: entry.durchgefuehrte_massnahmen,
        noch_umzusetzende_massnahmen: entry.noch_umzusetzende_massnahmen,
        sonstiges: entry.sonstiges,
        strecklaenge_km: entry.strecklaenge_km,
        gesamtkosten_mio_eur: entry.gesamtkosten_mio_eur,
        entwurfsgeschwindigkeit: entry.entwurfsgeschwindigkeit,
        planungsstand: entry.planungsstand,
        status_planung: entry.status_planung,
        status_bau: entry.status_bau,
        status_abgeschlossen: entry.status_abgeschlossen,
        ai_extracted: entry.ai_extracted,
        pfa_entries: entry.pfa_entries,
        project_ids: entry.project_ids,
        report_year: entry.year,
    };
}

function VibTabContent({
    entry,
    canEdit,
    onEdit,
}: {
    entry: VibEntryForProject;
    canEdit: boolean;
    onEdit: (entry: VibEntryForProject) => void;
}) {
    const [rawExpanded, setRawExpanded] = useState(false);
    const [pfaExpanded, setPfaExpanded] = useState(false);

    return (
        <Stack gap="md">
            <Group gap="sm" justify="space-between" align="flex-start">
                <Group gap="sm">
                    <ChronicleDataChip>{entry.category}</ChronicleDataChip>
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
                        <ChronicleDataChip>KI-extrahiert</ChronicleDataChip>
                    )}
                    {entry.status_planung && (
                        <ChronicleDataChip>Planung</ChronicleDataChip>
                    )}
                    {entry.status_bau && (
                        <ChronicleDataChip>Bau</ChronicleDataChip>
                    )}
                    {entry.status_abgeschlossen && (
                        <ChronicleDataChip>Abgeschlossen</ChronicleDataChip>
                    )}
                </Group>
                {canEdit && (
                    <Button size="xs" variant="light" onClick={() => onEdit(entry)}>
                        Bearbeiten
                    </Button>
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
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.planungsstand}</ReactMarkdown>
                </div>
            )}

            {/* Verkehrliche Zielsetzung */}
            {entry.verkehrliche_zielsetzung && (
                <div>
                    <Text size="sm" fw={600} mb={4}>
                        Verkehrliche Zielsetzung
                    </Text>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.verkehrliche_zielsetzung}</ReactMarkdown>
                </div>
            )}

            {/* Durchgeführte Maßnahmen */}
            {entry.durchgefuehrte_massnahmen && (
                <div>
                    <Text size="sm" fw={600} mb={4}>
                        Durchgeführte Maßnahmen
                    </Text>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.durchgefuehrte_massnahmen}</ReactMarkdown>
                </div>
            )}

            {/* Noch umzusetzende Maßnahmen */}
            {entry.noch_umzusetzende_massnahmen && (
                <div>
                    <Text size="sm" fw={600} mb={4}>
                        Noch umzusetzende Maßnahmen
                    </Text>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.noch_umzusetzende_massnahmen}</ReactMarkdown>
                </div>
            )}

            {/* Bauaktivitäten */}
            {entry.bauaktivitaeten && (
                <div>
                    <Text size="sm" fw={600} mb={4}>
                        Bauaktivitäten {entry.year}
                    </Text>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.bauaktivitaeten}</ReactMarkdown>
                </div>
            )}

            {/* Teilinbetriebnahmen */}
            {entry.teilinbetriebnahmen && (
                <div>
                    <Text size="sm" fw={600} mb={4}>
                        Teilinbetriebnahmen {entry.year}
                    </Text>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.teilinbetriebnahmen}</ReactMarkdown>
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
                        <div style={{ overflow: "auto", background: "var(--bg)", border: "1px solid var(--rule)", borderRadius: 0 }}>
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
                        </div>
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
    const { user } = useAuth();
    const [editingEntry, setEditingEntry] = useState<VibEntrySchema | null>(null);

    const canEdit = user?.role === "editor" || user?.role === "admin";

    if (isLoading) {
        return (
            <ChronicleCard>
                <Stack gap="sm">
                    <Title order={4}>Verkehrsinvestitionsberichte</Title>
                    <Group justify="center">
                        <Loader size="sm" />
                    </Group>
                </Stack>
            </ChronicleCard>
        );
    }

    if (!entries || entries.length === 0) {
        return null;
    }

    // Group by year (entries are already sorted newest first)
    const years = [...new Set(entries.map((e) => e.year))];

    return (
        <>
            <ChronicleCard>
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
                                            <VibTabContent
                                                key={entry.id}
                                                entry={entry}
                                                canEdit={canEdit}
                                                onEdit={(e) => setEditingEntry(toVibEntrySchema(e))}
                                            />
                                        ))}
                                    </Stack>
                                </Tabs.Panel>
                            );
                        })}
                    </Tabs>
                </Stack>
            </ChronicleCard>

            <VibEntryEditDrawer
                entry={editingEntry}
                opened={editingEntry !== null}
                onClose={() => setEditingEntry(null)}
            />
        </>
    );
}
