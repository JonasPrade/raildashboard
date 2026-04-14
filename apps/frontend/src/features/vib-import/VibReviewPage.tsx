import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
    ActionIcon,
    Alert,
    Box,
    Button,
    Checkbox,
    Container,
    Group,
    Loader,
    MultiSelect,
    Stack,
    Table,
    Text,
    Textarea,
    Tooltip,
} from "@mantine/core";
import { ChronicleHeadline, ChronicleCard, ChronicleDataChip } from "../../components/chronicle";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { IconChevronLeft, IconChevronRight } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { useAuth } from "../../lib/auth";
import { filterProjectOption } from "../../lib/filterProjectOption";
import {
    useVibParseResult,
    useConfirmVibImport,
    useProjects,
    useSaveVibDraft,
    useRetryVibAiForEntry,
    useVibAiAvailable,
    useVibOcrAvailable,
    type VibEntryProposed,
    type VibConfirmEntryInput,
} from "../../shared/api/queries";

const CATEGORY_COLORS: Record<string, string> = {
    laufend: "blue",
    neu: "green",
    potentiell: "yellow",
    abgeschlossen: "gray",
};

function VibEntryCard({
    entry,
    projectOptions,
    onProjectChange,
    onStatusChange,
    onRawTextChange,
    onFieldChange,
    onPfaChange,
    onPfaAdd,
    onPfaRemove,
    onRetryAi,
    isRetryingAi,
}: {
    entry: VibEntryProposed;
    projectOptions: { value: string; label: string }[];
    onProjectChange: (projectIds: number[]) => void;
    onStatusChange: (field: "status_planung" | "status_bau" | "status_abgeschlossen", value: boolean) => void;
    onRawTextChange: (text: string) => void;
    onFieldChange: (field: keyof VibEntryProposed, value: string) => void;
    onPfaChange: (pfaIndex: number, field: string, value: string) => void;
    onPfaAdd: () => void;
    onPfaRemove: (pfaIndex: number) => void;
    onRetryAi?: () => void;
    isRetryingAi?: boolean;
}) {
    const [showRawPfa, setShowRawPfa] = useState(false);

    const hasSuggestion =
        entry.project_ids.length > 0 ||
        (entry.suggested_project_ids && entry.suggested_project_ids.length > 0);
    const confidence =
        entry.project_ids.length > 0 &&
        entry.suggested_project_ids.some((id) => entry.project_ids.includes(id))
            ? "high"
            : entry.project_ids.length > 0
              ? "manual"
              : "none";

    return (
        <ChronicleCard>
            <Stack gap="md">
                {/* Section label + AI status badges */}
                <Group gap="xs" align="center">
                    {entry.vib_section && (
                        <Text size="xs" c="dimmed" ff="monospace">
                            {entry.vib_section}
                        </Text>
                    )}
                    {entry.ai_extracted && (
                        <ChronicleDataChip>KI</ChronicleDataChip>
                    )}
                    {entry.ai_extraction_failed && (
                        <Tooltip label={entry.ai_extraction_error ?? "KI-Extraktion fehlgeschlagen"} withArrow>
                            <ChronicleDataChip>KI fehlgeschlagen</ChronicleDataChip>
                        </Tooltip>
                    )}
                    {onRetryAi && (
                        <Button
                            size="xs"
                            variant="light"
                            color={entry.ai_extraction_failed ? "orange" : "violet"}
                            loading={isRetryingAi}
                            onClick={onRetryAi}
                        >
                            {entry.ai_extracted || entry.ai_extraction_failed
                                ? "KI wiederholen"
                                : "KI extrahieren"}
                        </Button>
                    )}
                </Group>

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

                {/* Project mapping */}
                <Group gap="sm" align="flex-end" wrap="wrap">
                    <MultiSelect
                        label="Projekte zuordnen"
                        size="sm"
                        clearable
                        searchable
                        filter={filterProjectOption}
                        placeholder="Projekte zuordnen…"
                        data={projectOptions}
                        value={entry.project_ids.map(String)}
                        onChange={(vs) => onProjectChange(vs.map(Number))}
                        style={{ flex: 1, minWidth: 200 }}
                    />
                    {hasSuggestion && (
                        <Tooltip label={`KI-Vorschlag: ${entry.suggested_project_ids.map(id => projectOptions.find(o => o.value === String(id))?.label ?? String(id)).join(", ")}`}>
                            <ChronicleDataChip style={{ cursor: "default", marginBottom: 6 }}>
                                {confidence === "high" ? "✓" : confidence === "manual" ? "~" : "?"}
                            </ChronicleDataChip>
                        </Tooltip>
                    )}
                </Group>

                {/* Projektstatus – drei Checkboxen */}
                <Group gap="lg">
                    <Text size="sm" fw={500} style={{ minWidth: 100 }}>Projektstatus</Text>
                    <Checkbox
                        label="Planung"
                        checked={entry.status_planung}
                        onChange={(e) => onStatusChange("status_planung", e.currentTarget.checked)}
                    />
                    <Checkbox
                        label="Bau"
                        checked={entry.status_bau}
                        onChange={(e) => onStatusChange("status_bau", e.currentTarget.checked)}
                    />
                    <Checkbox
                        label="Abgeschlossen"
                        checked={entry.status_abgeschlossen}
                        onChange={(e) => onStatusChange("status_abgeschlossen", e.currentTarget.checked)}
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

                {/* PFA-Tabelle — always shown, inline editable */}
                <div>
                    <Group justify="space-between" mb={6}>
                        <Text size="sm" fw={600}>
                            PFA-Tabelle ({entry.pfa_entries.length} Einträge)
                        </Text>
                        <Button size="xs" variant="light" onClick={onPfaAdd}>
                            + Zeile
                        </Button>
                    </Group>
                    {entry.pfa_entries.length > 0 ? (
                        <ChronicleCard style={{ overflow: "auto", padding: 0 }}>
                            <Table withTableBorder withColumnBorders fz="xs" style={{ fontSize: 11 }}>
                                <Table.Thead>
                                    <Table.Tr>
                                        <Table.Th>Nr.</Table.Th>
                                        <Table.Th>Örtlichkeit</Table.Th>
                                        <Table.Th>Entwurfspl.</Table.Th>
                                        <Table.Th>Abschluss FinVe</Table.Th>
                                        <Table.Th>PFB</Table.Th>
                                        <Table.Th>Baubeginn</Table.Th>
                                        <Table.Th>IBM</Table.Th>
                                        <Table.Th />
                                    </Table.Tr>
                                </Table.Thead>
                                <Table.Tbody>
                                    {entry.pfa_entries.map((pfa, pi) => (
                                        <Table.Tr key={pi}>
                                            {(["nr_pfa", "oertlichkeit", "entwurfsplanung", "abschluss_finve", "datum_pfb", "baubeginn", "inbetriebnahme"] as const).map((field) => (
                                                <Table.Td key={field}>
                                                    <input
                                                        style={{
                                                            width: field === "oertlichkeit" ? 140 : 80,
                                                            border: "none",
                                                            background: "transparent",
                                                            fontSize: 11,
                                                            fontFamily: "inherit",
                                                        }}
                                                        value={(pfa as Record<string, string | null>)[field] ?? ""}
                                                        onChange={(e) => onPfaChange(pi, field, e.currentTarget.value)}
                                                    />
                                                </Table.Td>
                                            ))}
                                            <Table.Td>
                                                <button
                                                    style={{ cursor: "pointer", background: "none", border: "none", color: "red" }}
                                                    onClick={() => onPfaRemove(pi)}
                                                    title="Zeile löschen"
                                                >
                                                    ×
                                                </button>
                                            </Table.Td>
                                        </Table.Tr>
                                    ))}
                                </Table.Tbody>
                            </Table>
                        </ChronicleCard>
                    ) : (
                        <Text size="xs" c="dimmed">Keine PFA-Einträge.</Text>
                    )}
                </div>

                {/* PFA raw-markdown toggle */}
                {entry.pfa_raw_markdown && (
                    <div>
                        <Button
                            size="xs"
                            variant="subtle"
                            onClick={() => setShowRawPfa((v) => !v)}
                            mb={4}
                        >
                            {showRawPfa ? "Roh-Markdown ausblenden" : "PFA Roh-Markdown anzeigen"}
                        </Button>
                        {showRawPfa && (
                            <Box
                                p="xs"
                                style={{
                                    fontSize: 12,
                                    fontFamily: "var(--mantine-font-family-monospace)",
                                    background: "var(--mantine-color-gray-0)",
                                    borderRadius: 4,
                                    overflowX: "auto",
                                }}
                                className="vib-raw-markdown"
                            >
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {entry.pfa_raw_markdown}
                                </ReactMarkdown>
                            </Box>
                        )}
                    </div>
                )}

                {/* Sonstiges — leftover text not assigned to any sub-section, always shown */}
                <Textarea
                    label="Sonstiger Text (nicht zugeordnet)"
                    autosize
                    minRows={3}
                    maxRows={12}
                    value={entry.sonstiges ?? ""}
                    onChange={(e) => onFieldChange("sonstiges", e.currentTarget.value)}
                    styles={{ input: { fontFamily: "monospace", fontSize: 12 } }}
                />

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
        </ChronicleCard>
    );
}

export default function VibReviewPage() {
    const { taskId } = useParams<{ taskId: string }>();
    const navigate = useNavigate();
    const { user } = useAuth();

    const { data: parseResult, isLoading, isError } = useVibParseResult(taskId ?? null);
    const { data: projects } = useProjects();
    const { data: aiAvailable } = useVibAiAvailable();
    const { data: ocrAvailable } = useVibOcrAvailable();
    const confirm = useConfirmVibImport();
    const saveDraft = useSaveVibDraft();
    const retryAi = useRetryVibAiForEntry();

    const [entries, setEntries] = useState<VibEntryProposed[] | null>(null);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [retryingIdx, setRetryingIdx] = useState<number | null>(null);

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

    const handlePfaChange = (idx: number) => (pfaIdx: number, field: string, value: string) => {
        setEntries((prev) =>
            (prev ?? parseResult.entries).map((e, i) => {
                if (i !== idx) return e;
                const newPfa = e.pfa_entries.map((p, pi) =>
                    pi === pfaIdx ? { ...p, [field]: value || null } : p
                );
                return { ...e, pfa_entries: newPfa };
            })
        );
    };

    const handlePfaAdd = (idx: number) => () => {
        setEntries((prev) =>
            (prev ?? parseResult.entries).map((e, i) => {
                if (i !== idx) return e;
                return {
                    ...e,
                    pfa_entries: [
                        ...e.pfa_entries,
                        {
                            nr_pfa: null,
                            oertlichkeit: null,
                            entwurfsplanung: null,
                            abschluss_finve: null,
                            datum_pfb: null,
                            baubeginn: null,
                            inbetriebnahme: null,
                            abschnitt_label: null,
                        },
                    ],
                };
            })
        );
    };

    const handlePfaRemove = (idx: number) => (pfaIdx: number) => {
        setEntries((prev) =>
            (prev ?? parseResult.entries).map((e, i) => {
                if (i !== idx) return e;
                return { ...e, pfa_entries: e.pfa_entries.filter((_, pi) => pi !== pfaIdx) };
            })
        );
    };

    const handleSaveDraft = async () => {
        if (!taskId || !parseResult) return;
        try {
            await saveDraft.mutateAsync({
                taskId,
                data: {
                    year: parseResult.year,
                    drucksache_nr: parseResult.drucksache_nr,
                    report_date: parseResult.report_date,
                    entries: displayEntries,
                },
            });
            notifications.show({ color: "green", message: "Entwurf gespeichert." });
        } catch {
            notifications.show({ color: "red", message: "Entwurf konnte nicht gespeichert werden." });
        }
    };

    const handleRetryAi = async (idx: number) => {
        if (!taskId) return;
        setRetryingIdx(idx);
        try {
            const updated = await retryAi.mutateAsync({ taskId, entryIdx: idx });
            setEntries((prev) =>
                (prev ?? parseResult.entries).map((e, i) => (i === idx ? updated : e))
            );
            notifications.show({ color: "green", message: "KI-Extraktion erfolgreich." });
        } catch {
            notifications.show({ color: "red", message: "KI-Extraktion fehlgeschlagen." });
        } finally {
            setRetryingIdx(null);
        }
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

    const matchedCount = displayEntries.filter((e) => e.project_ids.length > 0).length;
    const failedAiCount = displayEntries.filter((e) => e.ai_extraction_failed).length;

    return (
        <Container size="lg" py="xl">
            <Stack gap="lg">
                {/* Header */}
                <Group justify="space-between" align="flex-start">
                    <Stack gap={2}>
                        <ChronicleHeadline as="h1">VIB-Review — Berichtsjahr {parseResult.year}</ChronicleHeadline>
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
                        {failedAiCount > 0 && (
                            <Tooltip label={`${failedAiCount} Einträge: KI-Extraktion fehlgeschlagen`} withArrow>
                                <ChronicleDataChip>
                                    {failedAiCount} KI ✗
                                </ChronicleDataChip>
                            </Tooltip>
                        )}
                        <Tooltip label={ocrAvailable?.available ? `OCR: ${ocrAvailable.model}` : "Texterkennung: pymupdf"}>
                            <ChronicleDataChip>
                                {ocrAvailable?.available ? "Mistral OCR" : "pymupdf"}
                            </ChronicleDataChip>
                        </Tooltip>
                        <Button
                            variant="light"
                            onClick={handleSaveDraft}
                            loading={saveDraft.isPending}
                        >
                            Entwurf speichern
                        </Button>
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
                    <ChronicleDataChip>
                        {currentEntry.category}
                    </ChronicleDataChip>
                    {currentEntry.ai_extraction_failed && (
                        <Tooltip label={currentEntry.ai_extraction_error ?? "KI-Extraktion fehlgeschlagen – Wiederholen im Eintrag möglich"} withArrow>
                            <ChronicleDataChip>KI ✗</ChronicleDataChip>
                        </Tooltip>
                    )}
                </Group>

                {/* Entry card */}
                {currentEntry && (
                    <VibEntryCard
                        entry={currentEntry}
                        projectOptions={projectOptions}
                        onProjectChange={(projectIds) => updateCurrentEntry({ project_ids: projectIds })}
                        onStatusChange={(field, value) =>
                            updateCurrentEntry({ [field]: value })
                        }
                        onRawTextChange={(text) => updateCurrentEntry({ raw_text: text })}
                        onFieldChange={handleFieldChange(currentIndex)}
                        onPfaChange={handlePfaChange(currentIndex)}
                        onPfaAdd={handlePfaAdd(currentIndex)}
                        onPfaRemove={handlePfaRemove(currentIndex)}
                        onRetryAi={aiAvailable?.available ? () => handleRetryAi(currentIndex) : undefined}
                        isRetryingAi={retryingIdx === currentIndex}
                    />
                )}
            </Stack>
        </Container>
    );
}
