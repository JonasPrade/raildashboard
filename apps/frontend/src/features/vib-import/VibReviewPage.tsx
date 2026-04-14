import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
    ActionIcon,
    Alert,
    Button,
    Container,
    Group,
    Loader,
    Select,
    Stack,
    Text,
    Tooltip,
} from "@mantine/core";
import { ChronicleHeadline, ChronicleDataChip } from "../../components/chronicle";
import { IconChevronLeft, IconChevronRight } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { useAuth } from "../../lib/auth";
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
import VibEntryEditForm from "./VibEntryEditForm";

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
                    <Group gap={4} align="center">
                        <Select
                            data={displayEntries.map((_, i) => ({ value: String(i + 1), label: String(i + 1) }))}
                            value={String(currentIndex + 1)}
                            onChange={(v) => v && setCurrentIndex(Number(v) - 1)}
                            searchable
                            size="xs"
                            w={70}
                            styles={{ input: { textAlign: "center", fontWeight: 500 } }}
                            comboboxProps={{ withinPortal: true }}
                        />
                        <Text size="sm" fw={500}>/ {total}</Text>
                    </Group>
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

                {/* Entry form */}
                {currentEntry && (
                    <VibEntryEditForm
                        entry={currentEntry}
                        projectOptions={projectOptions}
                        onChange={updateCurrentEntry}
                        onRetryAi={aiAvailable?.available ? () => handleRetryAi(currentIndex) : undefined}
                        isRetryingAi={retryingIdx === currentIndex}
                    />
                )}
            </Stack>
        </Container>
    );
}
