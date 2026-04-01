import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
    ActionIcon,
    Alert,
    Badge,
    Button,
    Card,
    Container,
    Group,
    Loader,
    Paper,
    Select,
    Stack,
    Table,
    Text,
    Textarea,
    Title,
    Tooltip,
} from "@mantine/core";
import { IconChevronLeft, IconChevronRight } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { useAuth } from "../../lib/auth";
import {
    useVibParseResult,
    useConfirmVibImport,
    useProjects,
    type VibEntryProposed,
    type VibConfirmEntryInput,
} from "../../shared/api/queries";

const CATEGORY_COLORS: Record<string, string> = {
    laufend: "blue",
    neu: "green",
    potentiell: "yellow",
    abgeschlossen: "gray",
};

const PROJECT_STATUS_OPTIONS = [
    { value: "Planung", label: "Planung" },
    { value: "Bau", label: "Bau" },
];

function VibEntryCard({
    entry,
    projectOptions,
    onProjectChange,
    onStatusChange,
    onRawTextChange,
    onFieldChange,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    onPfaChange: _onPfaChange,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    onPfaAdd: _onPfaAdd,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    onPfaRemove: _onPfaRemove,
}: {
    entry: VibEntryProposed;
    projectOptions: { value: string; label: string }[];
    onProjectChange: (projectId: number | null) => void;
    onStatusChange: (status: string | null) => void;
    onRawTextChange: (text: string) => void;
    onFieldChange: (field: keyof VibEntryProposed, value: string) => void;
    onPfaChange: (pfaIndex: number, field: string, value: string) => void;
    onPfaAdd: () => void;
    onPfaRemove: (pfaIndex: number) => void;
}) {
    const hasSuggestion =
        entry.project_id !== null ||
        (entry.suggested_project_ids && entry.suggested_project_ids.length > 0);
    const confidence =
        entry.project_id !== null && entry.suggested_project_ids[0] === entry.project_id
            ? "high"
            : entry.project_id !== null
              ? "manual"
              : "none";

    return (
        <Card withBorder radius="md" padding="lg" shadow="xs">
            <Stack gap="md">
                {/* Section label */}
                {entry.vib_section && (
                    <Text size="xs" c="dimmed" ff="monospace">
                        {entry.vib_section}
                    </Text>
                )}
                {(entry as VibEntryProposed & { ai_extracted?: boolean }).ai_extracted && (
                    <Badge size="xs" color="violet" variant="light">KI</Badge>
                )}

                {/* Projektkenndaten */}
                {(entry.strecklaenge_km !== null ||
                    entry.gesamtkosten_mio_eur !== null ||
                    entry.entwurfsgeschwindigkeit) && (
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

                {/* Planungsstand (extracted from PDF) */}
                <Textarea
                    label="Planungsstand"
                    autosize
                    minRows={3}
                    maxRows={12}
                    value={entry.planungsstand ?? ""}
                    onChange={(e) => onFieldChange("planungsstand", e.currentTarget.value)}
                    styles={{ input: { fontFamily: "monospace", fontSize: 12 } }}
                />

                {/* Project mapping + status */}
                <Group gap="sm" align="flex-end" wrap="wrap">
                    <Select
                        label="Projekt zuordnen"
                        size="sm"
                        clearable
                        searchable
                        placeholder="Projekt zuordnen…"
                        data={projectOptions}
                        value={entry.project_id !== null ? String(entry.project_id) : null}
                        onChange={(v) => onProjectChange(v !== null ? Number(v) : null)}
                        style={{ flex: 1, minWidth: 200 }}
                    />
                    {hasSuggestion && (
                        <Tooltip label={`KI-Vorschlag: ${entry.suggested_project_ids.join(", ")}`}>
                            <Badge
                                size="xs"
                                color={
                                    confidence === "high"
                                        ? "green"
                                        : confidence === "manual"
                                          ? "yellow"
                                          : "red"
                                }
                                variant="dot"
                                style={{ cursor: "default", marginBottom: 6 }}
                            >
                                {confidence === "high" ? "✓" : confidence === "manual" ? "~" : "?"}
                            </Badge>
                        </Tooltip>
                    )}
                    <Select
                        label="Projektstatus"
                        size="sm"
                        clearable
                        placeholder="–"
                        data={PROJECT_STATUS_OPTIONS}
                        value={entry.project_status ?? null}
                        onChange={onStatusChange}
                        style={{ width: 150 }}
                    />
                </Group>

                {/* Bauaktivitäten */}
                <Textarea
                    label="Bauaktivitäten"
                    autosize
                    minRows={3}
                    maxRows={12}
                    value={entry.bauaktivitaeten ?? ""}
                    onChange={(e) => onFieldChange("bauaktivitaeten", e.currentTarget.value)}
                    styles={{ input: { fontFamily: "monospace", fontSize: 12 } }}
                />

                {/* Teilinbetriebnahmen */}
                <Textarea
                    label="Teilinbetriebnahmen"
                    autosize
                    minRows={3}
                    maxRows={12}
                    value={entry.teilinbetriebnahmen ?? ""}
                    onChange={(e) => onFieldChange("teilinbetriebnahmen", e.currentTarget.value)}
                    styles={{ input: { fontFamily: "monospace", fontSize: 12 } }}
                />

                {/* Verkehrliche Zielsetzung */}
                <Textarea
                    label="Verkehrliche Zielsetzung"
                    autosize
                    minRows={3}
                    maxRows={12}
                    value={entry.verkehrliche_zielsetzung ?? ""}
                    onChange={(e) => onFieldChange("verkehrliche_zielsetzung", e.currentTarget.value)}
                    styles={{ input: { fontFamily: "monospace", fontSize: 12 } }}
                />

                {/* Durchgeführte Maßnahmen */}
                <Textarea
                    label="Durchgeführte Maßnahmen"
                    autosize
                    minRows={3}
                    maxRows={12}
                    value={entry.durchgefuehrte_massnahmen ?? ""}
                    onChange={(e) => onFieldChange("durchgefuehrte_massnahmen", e.currentTarget.value)}
                    styles={{ input: { fontFamily: "monospace", fontSize: 12 } }}
                />

                {/* Noch umzusetzende Maßnahmen */}
                <Textarea
                    label="Noch umzusetzende Maßnahmen"
                    autosize
                    minRows={3}
                    maxRows={12}
                    value={entry.noch_umzusetzende_massnahmen ?? ""}
                    onChange={(e) => onFieldChange("noch_umzusetzende_massnahmen", e.currentTarget.value)}
                    styles={{ input: { fontFamily: "monospace", fontSize: 12 } }}
                />

                {/* PFA-Tabelle — always shown */}
                {entry.pfa_entries && entry.pfa_entries.length > 0 && (
                    <div>
                        <Text size="sm" fw={600} mb={6}>
                            PFA-Tabelle ({entry.pfa_entries.length} Einträge)
                        </Text>
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
                                    {entry.pfa_entries.map((pfa, pi) => (
                                        <Table.Tr key={pi}>
                                            <Table.Td>
                                                {pfa.abschnitt_label
                                                    ? `${pfa.abschnitt_label} / `
                                                    : ""}
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
                    </div>
                )}

                {/* Volltext — always shown, editable */}
                {entry.raw_text !== null && entry.raw_text !== undefined && (
                    <Textarea
                        label="Volltext"
                        autosize
                        minRows={6}
                        maxRows={24}
                        value={entry.raw_text}
                        onChange={(e) => onRawTextChange(e.currentTarget.value)}
                        styles={{
                            input: {
                                fontFamily: "monospace",
                                fontSize: 12,
                                lineHeight: 1.6,
                            },
                        }}
                    />
                )}
            </Stack>
        </Card>
    );
}

export default function VibReviewPage() {
    const { taskId } = useParams<{ taskId: string }>();
    const navigate = useNavigate();
    const { user } = useAuth();

    const { data: parseResult, isLoading, isError } = useVibParseResult(taskId ?? null);
    const { data: projects } = useProjects();
    const confirm = useConfirmVibImport();

    const [entries, setEntries] = useState<VibEntryProposed[] | null>(null);
    const [currentIndex, setCurrentIndex] = useState(0);

    if (user?.role !== "editor" && user?.role !== "admin") {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Kein Zugriff">
                    Diese Seite ist nur für Editoren und Administratoren zugänglich.
                </Alert>
            </Container>
        );
    }

    if (isLoading) {
        return (
            <Container py="xl">
                <Group justify="center">
                    <Loader />
                </Group>
            </Container>
        );
    }

    if (isError || !parseResult) {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Fehler">
                    Parse-Ergebnis konnte nicht geladen werden. Möglicherweise ist der Task noch
                    nicht abgeschlossen.
                </Alert>
            </Container>
        );
    }

    const displayEntries: VibEntryProposed[] = entries ?? parseResult.entries;
    const total = displayEntries.length;
    const currentEntry = displayEntries[currentIndex];

    const projectOptions = (projects ?? []).map((p) => ({
        value: String(p.id),
        label: `${p.project_number ?? "–"} ${p.name}`,
    }));

    const updateCurrentEntry = (patch: Partial<VibEntryProposed>) => {
        setEntries((prev) => {
            const base = prev ?? parseResult.entries;
            return base.map((e, i) => (i === currentIndex ? { ...e, ...patch } : e));
        });
    };

    const handleFieldChange = (idx: number) => (field: keyof VibEntryProposed, value: string) => {
        setEntries((prev) =>
            (prev ?? parseResult.entries).map((e, i) => (i === idx ? { ...e, [field]: value || null } : e))
        );
    };

    const handleConfirm = async () => {
        if (!taskId) return;
        const payload = {
            task_id: taskId,
            year: parseResult.year,
            drucksache_nr: parseResult.drucksache_nr,
            report_date: parseResult.report_date,
            entries: displayEntries.map(
                // eslint-disable-next-line @typescript-eslint/no-unused-vars
                ({ suggested_project_ids, ...rest }): VibConfirmEntryInput => rest,
            ),
        };
        try {
            const res = await confirm.mutateAsync(payload);
            notifications.show({
                color: "green",
                message: `Import erfolgreich: ${res.entries_created} Vorhaben, ${res.pfa_entries_created} PFA-Einträge importiert.`,
            });
            navigate("/admin/vib-import");
        } catch (e: unknown) {
            const msg = (e as { message?: string })?.message ?? "Unbekannter Fehler";
            notifications.show({ color: "red", message: `Fehler: ${msg}` });
        }
    };

    const matchedCount = displayEntries.filter((e) => e.project_id !== null).length;

    return (
        <Container size="lg" py="xl">
            <Stack gap="lg">
                {/* Header */}
                <Group justify="space-between" align="flex-start">
                    <Stack gap={2}>
                        <Title order={2}>VIB-Review — Berichtsjahr {parseResult.year}</Title>
                        <Text size="sm" c="dimmed">
                            {parseResult.drucksache_nr
                                ? `Drucksache ${parseResult.drucksache_nr}`
                                : ""}
                            {parseResult.report_date ? ` · ${parseResult.report_date}` : ""}
                        </Text>
                    </Stack>
                    <Group gap="sm">
                        <Text size="sm" c="dimmed">
                            {matchedCount} / {total} zugeordnet
                        </Text>
                        <Button variant="outline" onClick={() => navigate("/admin/vib-import")}>
                            Abbrechen
                        </Button>
                        <Button onClick={handleConfirm} loading={confirm.isPending} color="green">
                            Import bestätigen
                        </Button>
                    </Group>
                </Group>

                {/* Navigation bar */}
                <Group gap="xs" align="center">
                    <ActionIcon
                        variant="default"
                        onClick={() => setCurrentIndex((i) => i - 1)}
                        disabled={currentIndex === 0}
                    >
                        <IconChevronLeft size={16} />
                    </ActionIcon>
                    <Text size="sm" fw={500} style={{ minWidth: 52, textAlign: "center" }}>
                        {currentIndex + 1} / {total}
                    </Text>
                    <ActionIcon
                        variant="default"
                        onClick={() => setCurrentIndex((i) => i + 1)}
                        disabled={currentIndex === total - 1}
                    >
                        <IconChevronRight size={16} />
                    </ActionIcon>
                    <Text fw={600} lineClamp={1} style={{ maxWidth: 500 }}>
                        {currentEntry.vib_name_raw}
                    </Text>
                    <Badge
                        size="sm"
                        color={CATEGORY_COLORS[currentEntry.category] ?? "gray"}
                        variant="light"
                    >
                        {currentEntry.category}
                    </Badge>
                </Group>

                {/* Entry card */}
                {currentEntry && (
                    <VibEntryCard
                        entry={currentEntry}
                        projectOptions={projectOptions}
                        onProjectChange={(projectId) => updateCurrentEntry({ project_id: projectId })}
                        onStatusChange={(status) =>
                            updateCurrentEntry({
                                project_status: status as "Planung" | "Bau" | null,
                            })
                        }
                        onRawTextChange={(text) => updateCurrentEntry({ raw_text: text })}
                        onFieldChange={handleFieldChange(currentIndex)}
                        onPfaChange={() => {}}
                        onPfaAdd={() => {}}
                        onPfaRemove={() => {}}
                    />
                )}
            </Stack>
        </Container>
    );
}
