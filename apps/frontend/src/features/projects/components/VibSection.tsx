import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, ChevronDown, ChevronUp } from "lucide-react";
import {
    Badge,
    Button,
    Collapse,
    Group,
    Paper,
    Stack,
    Table,
    Tabs,
    Text,
    Title,
} from "@mantine/core";
import { ResponsiveTable } from "../../../shared/ui/ResponsiveTable";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { notifications } from "@mantine/notifications";
import {
    type VibEntryForProject,
    type VibEntrySchema,
    useProjectOptions,
    useProjectVibEntries,
    useUpdateVibEntry,
} from "../../../shared/api/queries";
import { useAuth } from "../../../lib/auth";
import VibEntryEditDrawer from "../../vib-import/VibEntryEditDrawer";
import { LoadingState } from "../../../shared/ui/LoadingState";

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
        confirmed: entry.confirmed,
        assignment_note: entry.assignment_note,
        page: entry.page,
        pfa_entries: entry.pfa_entries,
        project_ids: entry.project_ids,
        report_year: entry.year,
    };
}

/** Link button to the (sub)project a PFA section is assigned to. */
function PfaProjectLink({ projectId, name }: { projectId: number; name: string | undefined }) {
    const label = name ?? `Projekt ${projectId}`;
    return (
        <Button
            component={Link}
            to={`/projects/${projectId}`}
            variant="light"
            size="compact-xs"
            rightSection={<ArrowRight size={12} aria-hidden />}
            title={`Zum Projekt: ${label}`}
            styles={{ root: { maxWidth: 220 }, label: { overflow: "hidden", textOverflow: "ellipsis" } }}
        >
            {label}
        </Button>
    );
}

function VibTabContent({
    entry,
    canEdit,
    onEdit,
    projectNames,
}: {
    entry: VibEntryForProject;
    canEdit: boolean;
    onEdit: (entry: VibEntryForProject) => void;
    projectNames: Map<number, string>;
}) {
    const [rawExpanded, setRawExpanded] = useState(false);
    const [pfaExpanded, setPfaExpanded] = useState(false);
    const updateEntry = useUpdateVibEntry();

    const handleConfirm = async () => {
        try {
            await updateEntry.mutateAsync({ entryId: entry.id, data: { confirmed: true } });
            notifications.show({ color: "green", message: "VIB-Eintrag bestätigt." });
        } catch {
            notifications.show({ color: "red", message: "VIB-Eintrag konnte nicht bestätigt werden." });
        }
    };

    return (
        <Stack gap="md">
            <Group gap="sm" justify="space-between" align="flex-start">
                <Group gap="sm">
                    <Badge variant="outline">{entry.category}</Badge>
                    {entry.vib_section && (
                        <Text size="xs" c="dimmed">
                            {entry.vib_section}
                        </Text>
                    )}
                    {entry.drucksache_nr && (
                        <Text size="xs" c="dimmed">
                            Drucksache {entry.drucksache_nr}
                            {entry.page != null ? `, S. ${entry.page}` : ""}
                        </Text>
                    )}
                    {!entry.confirmed && (
                        <Badge variant="outline">unbestätigt</Badge>
                    )}
                    {entry.ai_extracted && (
                        <Badge variant="outline">KI-extrahiert</Badge>
                    )}
                    {entry.status_planung && (
                        <Badge variant="outline">Planung</Badge>
                    )}
                    {entry.status_bau && (
                        <Badge variant="outline">Bau</Badge>
                    )}
                    {entry.status_abgeschlossen && (
                        <Badge variant="outline">Abgeschlossen</Badge>
                    )}
                </Group>
                {canEdit && (
                    <Group gap="xs">
                        {!entry.confirmed && (
                            <Button size="xs" onClick={handleConfirm} loading={updateEntry.isPending}>
                                Bestätigen
                            </Button>
                        )}
                        <Button size="xs" variant="light" onClick={() => onEdit(entry)}>
                            Bearbeiten
                        </Button>
                    </Group>
                )}
            </Group>

            {!entry.confirmed && (
                <Text size="sm" c="dimmed">
                    Über MCP eingelesen und noch nicht bestätigt — fließt erst nach dem Bestätigen in den Planungsstand ein.
                </Text>
            )}
            {entry.assignment_note && (
                <Text size="sm" c="dimmed">
                    Zuordnung: {entry.assignment_note}
                </Text>
            )}

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
                        <Text size="xs" c="dimmed" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                            {pfaExpanded ? <ChevronUp size={16} aria-hidden /> : <ChevronDown size={16} aria-hidden />}
                            {pfaExpanded ? "ausblenden" : "anzeigen"}
                        </Text>
                    </Group>
                    <Collapse in={pfaExpanded}>
                        <div style={{ overflow: "auto", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 0 }}>
                            <ResponsiveTable minWidth={860} withTableBorder withColumnBorders fz="xs" style={{ fontSize: 11 }}>
                                <Table.Thead>
                                    <Table.Tr>
                                        <Table.Th>Nr.</Table.Th>
                                        <Table.Th>Örtlichkeit</Table.Th>
                                        <Table.Th>Abschluss FinVe</Table.Th>
                                        <Table.Th>PFB</Table.Th>
                                        <Table.Th>Baubeginn</Table.Th>
                                        <Table.Th>IBM</Table.Th>
                                        <Table.Th>Projekt</Table.Th>
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
                                            <Table.Td>
                                                {pfa.project_id != null ? (
                                                    <PfaProjectLink
                                                        projectId={pfa.project_id}
                                                        name={projectNames.get(pfa.project_id)}
                                                    />
                                                ) : (
                                                    "–"
                                                )}
                                            </Table.Td>
                                        </Table.Tr>
                                    ))}
                                </Table.Tbody>
                            </ResponsiveTable>
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
                        <Text size="xs" c="dimmed" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                            {rawExpanded ? <ChevronUp size={16} aria-hidden /> : <ChevronDown size={16} aria-hidden />}
                            {rawExpanded ? "ausblenden" : "anzeigen"}
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
    const { can } = useAuth();
    const [editingEntry, setEditingEntry] = useState<VibEntrySchema | null>(null);

    const canEdit = can("vib.import");

    // Names for the PFA → project links; the lightweight option list is only
    // fetched when at least one PFA section is assigned to a project.
    const hasPfaAssignment = !!entries?.some((e) => e.pfa_entries.some((p) => p.project_id != null));
    const { data: projectOptions } = useProjectOptions({ enabled: hasPfaAssignment });
    const projectNames = useMemo(
        () => new Map((projectOptions ?? []).map((p) => [p.id, p.name])),
        [projectOptions],
    );

    if (isLoading) {
        return (
            <Paper withBorder p="var(--card-pad)">
                <Stack gap="sm">
                    <Title order={2}>Verkehrsinvestitionsberichte</Title>
                    <LoadingState rows={3} />
                </Stack>
            </Paper>
        );
    }

    if (!entries || entries.length === 0) {
        return null;
    }

    // Group by year (entries are already sorted newest first)
    const years = [...new Set(entries.map((e) => e.year))];

    return (
        <>
            <Paper withBorder p="var(--card-pad)">
                <Stack gap="md">
                    <Title order={2}>Verkehrsinvestitionsberichte</Title>
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
                                                projectNames={projectNames}
                                                onEdit={(e) => setEditingEntry(toVibEntrySchema(e))}
                                            />
                                        ))}
                                    </Stack>
                                </Tabs.Panel>
                            );
                        })}
                    </Tabs>
                </Stack>
            </Paper>

            <VibEntryEditDrawer
                entry={editingEntry}
                opened={editingEntry !== null}
                onClose={() => setEditingEntry(null)}
            />
        </>
    );
}
