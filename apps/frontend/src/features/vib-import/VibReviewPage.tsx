import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
    Alert,
    Badge,
    Button,
    Collapse,
    Container,
    Group,
    Loader,
    Paper,
    Select,
    Stack,
    Table,
    Text,
    Title,
    Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useAuth } from "../../lib/auth";
import {
    useVibParseResult,
    useConfirmVibImport,
    useProjects,
    type VibEntryProposed,
    type VibConfirmEntryInput,
} from "../../shared/api/queries";

// Category badge colors
const CATEGORY_COLORS: Record<string, string> = {
    laufend: "blue",
    neu: "green",
    potentiell: "yellow",
    abgeschlossen: "gray",
};

// Single entry row with expandable details
function VibEntryRow({
    entry,
    index,
    projectOptions,
    onProjectChange,
}: {
    entry: VibEntryProposed;
    index: number;
    projectOptions: { value: string; label: string }[];
    onProjectChange: (index: number, projectId: number | null) => void;
}) {
    const [expanded, setExpanded] = useState(false);
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
        <>
            <Table.Tr>
                <Table.Td>
                    <Text size="xs" c="dimmed" ff="monospace">
                        {entry.vib_section ?? "–"}
                    </Text>
                </Table.Td>
                <Table.Td>
                    <Text size="sm" lineClamp={2} style={{ maxWidth: 360 }}>
                        {entry.vib_name_raw}
                    </Text>
                </Table.Td>
                <Table.Td>
                    <Badge
                        size="xs"
                        color={CATEGORY_COLORS[entry.category] ?? "gray"}
                        variant="light"
                    >
                        {entry.category}
                    </Badge>
                </Table.Td>
                <Table.Td style={{ minWidth: 260 }}>
                    <Group gap={4} align="center" wrap="nowrap">
                        <Select
                            size="xs"
                            clearable
                            searchable
                            placeholder="Projekt zuordnen…"
                            data={projectOptions}
                            value={entry.project_id !== null ? String(entry.project_id) : null}
                            onChange={(v) => onProjectChange(index, v !== null ? Number(v) : null)}
                            style={{ flex: 1 }}
                        />
                        {hasSuggestion && (
                            <Tooltip label={`KI-Vorschlag: ${entry.suggested_project_ids.join(", ")}`}>
                                <Badge
                                    size="xs"
                                    color={confidence === "high" ? "green" : confidence === "manual" ? "yellow" : "red"}
                                    variant="dot"
                                    style={{ cursor: "default" }}
                                >
                                    {confidence === "high" ? "✓" : confidence === "manual" ? "~" : "?"}
                                </Badge>
                            </Tooltip>
                        )}
                    </Group>
                </Table.Td>
                <Table.Td>
                    <Button
                        size="xs"
                        variant="subtle"
                        onClick={() => setExpanded((e) => !e)}
                    >
                        {expanded ? "▲" : "▼"}
                    </Button>
                </Table.Td>
            </Table.Tr>
            {expanded && (
                <Table.Tr>
                    <Table.Td colSpan={5} p={0}>
                        <Collapse in={expanded}>
                            <Paper bg="gray.0" p="md" m="xs" radius="sm">
                                <Stack gap="xs">
                                    {entry.strecklaenge_km !== null && (
                                        <Group gap="md">
                                            <Text size="xs">
                                                <b>Länge:</b> {entry.strecklaenge_km} km
                                            </Text>
                                            {entry.gesamtkosten_mio_eur !== null && (
                                                <Text size="xs">
                                                    <b>Gesamtkosten:</b>{" "}
                                                    {entry.gesamtkosten_mio_eur} Mio. €
                                                </Text>
                                            )}
                                            {entry.entwurfsgeschwindigkeit && (
                                                <Text size="xs">
                                                    <b>Vmax:</b> {entry.entwurfsgeschwindigkeit}{" "}
                                                    km/h
                                                </Text>
                                            )}
                                        </Group>
                                    )}
                                    {entry.bauaktivitaeten && (
                                        <div>
                                            <Text size="xs" fw={600}>
                                                Bauaktivitäten:
                                            </Text>
                                            <Text size="xs" style={{ whiteSpace: "pre-wrap" }}>
                                                {entry.bauaktivitaeten}
                                            </Text>
                                        </div>
                                    )}
                                    {entry.teilinbetriebnahmen && (
                                        <div>
                                            <Text size="xs" fw={600}>
                                                Teilinbetriebnahmen:
                                            </Text>
                                            <Text size="xs" style={{ whiteSpace: "pre-wrap" }}>
                                                {entry.teilinbetriebnahmen}
                                            </Text>
                                        </div>
                                    )}
                                    {entry.pfa_entries && entry.pfa_entries.length > 0 && (
                                        <div>
                                            <Text size="xs" fw={600} mb={4}>
                                                PFA-Tabelle ({entry.pfa_entries.length} Einträge):
                                            </Text>
                                            <Table
                                                withTableBorder
                                                withColumnBorders
                                                fz="xs"
                                                style={{ fontSize: 11 }}
                                            >
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
                                                            <Table.Td>
                                                                {pfa.oertlichkeit ?? "–"}
                                                            </Table.Td>
                                                            <Table.Td>
                                                                {pfa.abschluss_finve ?? "–"}
                                                            </Table.Td>
                                                            <Table.Td>
                                                                {pfa.datum_pfb ?? "–"}
                                                            </Table.Td>
                                                            <Table.Td>
                                                                {pfa.baubeginn ?? "–"}
                                                            </Table.Td>
                                                            <Table.Td>
                                                                {pfa.inbetriebnahme ?? "–"}
                                                            </Table.Td>
                                                        </Table.Tr>
                                                    ))}
                                                </Table.Tbody>
                                            </Table>
                                        </div>
                                    )}
                                    {entry.raw_text && (
                                        <details>
                                            <summary>
                                                <Text size="xs" span c="dimmed">
                                                    Volltext anzeigen
                                                </Text>
                                            </summary>
                                            <Text
                                                size="xs"
                                                c="dimmed"
                                                style={{ whiteSpace: "pre-wrap", marginTop: 4 }}
                                            >
                                                {entry.raw_text}
                                            </Text>
                                        </details>
                                    )}
                                </Stack>
                            </Paper>
                        </Collapse>
                    </Table.Td>
                </Table.Tr>
            )}
        </>
    );
}

export default function VibReviewPage() {
    const { taskId } = useParams<{ taskId: string }>();
    const navigate = useNavigate();
    const { user } = useAuth();

    const { data: parseResult, isLoading, isError } = useVibParseResult(taskId ?? null);
    const { data: projects } = useProjects();
    const confirm = useConfirmVibImport();

    // Local state for per-entry project assignments
    const [entries, setEntries] = useState<VibEntryProposed[] | null>(null);

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
                    Parse-Ergebnis konnte nicht geladen werden. Möglicherweise ist der
                    Task noch nicht abgeschlossen.
                </Alert>
            </Container>
        );
    }

    const displayEntries: VibEntryProposed[] = entries ?? parseResult.entries;

    const projectOptions = (projects ?? []).map((p) => ({
        value: String(p.id),
        label: `${p.project_number ?? "–"} ${p.name}`,
    }));

    const handleProjectChange = (index: number, projectId: number | null) => {
        setEntries((prev) => {
            const base = prev ?? parseResult.entries;
            return base.map((e, i) => (i === index ? { ...e, project_id: projectId } : e));
        });
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
                ({ suggested_project_ids, ...rest }): VibConfirmEntryInput => rest
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
        <Container size="xl" py="xl">
            <Stack gap="lg">
                <Group justify="space-between" align="flex-start">
                    <Stack gap={2}>
                        <Title order={2}>
                            VIB-Review — Berichtsjahr {parseResult.year}
                        </Title>
                        <Text size="sm" c="dimmed">
                            {parseResult.drucksache_nr
                                ? `Drucksache ${parseResult.drucksache_nr}`
                                : ""}
                            {parseResult.report_date ? ` · ${parseResult.report_date}` : ""}
                        </Text>
                    </Stack>
                    <Group gap="sm">
                        <Text size="sm" c="dimmed">
                            {matchedCount} / {displayEntries.length} Vorhaben zugeordnet
                        </Text>
                        <Button
                            variant="outline"
                            onClick={() => navigate("/admin/vib-import")}
                        >
                            Abbrechen
                        </Button>
                        <Button
                            onClick={handleConfirm}
                            loading={confirm.isPending}
                            color="green"
                        >
                            Import bestätigen
                        </Button>
                    </Group>
                </Group>

                <Paper withBorder p={0} style={{ overflow: "auto" }}>
                    <Table striped withTableBorder highlightOnHover>
                        <Table.Thead>
                            <Table.Tr>
                                <Table.Th w={90}>Abschnitt</Table.Th>
                                <Table.Th>Vorhabenname</Table.Th>
                                <Table.Th w={120}>Kategorie</Table.Th>
                                <Table.Th w={280}>Projekt</Table.Th>
                                <Table.Th w={50} />
                            </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                            {displayEntries.map((entry, i) => (
                                <VibEntryRow
                                    key={i}
                                    entry={entry}
                                    index={i}
                                    projectOptions={projectOptions}
                                    onProjectChange={handleProjectChange}
                                />
                            ))}
                        </Table.Tbody>
                    </Table>
                </Paper>
            </Stack>
        </Container>
    );
}
