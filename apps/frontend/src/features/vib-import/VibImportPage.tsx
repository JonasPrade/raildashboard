import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
    Alert,
    Button,
    Checkbox,
    Container,
    FileInput,
    Group,
    Loader,
    NumberInput,
    Progress,
    Stack,
    Table,
    Text,
} from "@mantine/core";
import { ChronicleHeadline, ChronicleCard } from "../../components/chronicle";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import { useAuth } from "../../lib/auth";
import {
    useStartVibImport,
    useTaskStatus,
    useVibReports,
    useDeleteVibReport,
    useVibDrafts,
    useDeleteVibDraft,
    type TaskProgressMeta,
} from "../../shared/api/queries";

export default function VibImportPage() {
    const { user } = useAuth();
    const navigate = useNavigate();

    const [file, setFile] = useState<File | null>(null);
    const [pdfUrl, setPdfUrl] = useState<string | null>(null);
    const [year, setYear] = useState<number>(new Date().getFullYear() - 1);
    const [startPage, setStartPage] = useState<number | "">("");
    const [endPage, setEndPage] = useState<number | "">("");
    const [stripHeadersFooters, setStripHeadersFooters] = useState(true);
    const [taskId, setTaskId] = useState<string | null>(null);

    useEffect(() => {
        if (!file) { setPdfUrl(null); return; }
        const url = URL.createObjectURL(file);
        setPdfUrl(url);
        return () => URL.revokeObjectURL(url);
    }, [file]);

    const startImport = useStartVibImport();
    const taskStatus = useTaskStatus(taskId);
    const { data: reports, isLoading: reportsLoading } = useVibReports();
    const deleteReport = useDeleteVibReport();
    const { data: drafts, isLoading: draftsLoading } = useVibDrafts();
    const deleteDraft = useDeleteVibDraft();

    if (user?.role !== "editor" && user?.role !== "admin") {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Kein Zugriff">
                    Diese Seite ist nur für Editoren und Administratoren zugänglich.
                </Alert>
            </Container>
        );
    }

    const handleUpload = async () => {
        if (!file) return;
        try {
            const { task_id } = await startImport.mutateAsync({
                pdf: file,
                year,
                startPage: startPage !== "" ? startPage : undefined,
                endPage: endPage !== "" ? endPage : undefined,
                stripHeadersFooters,
            });
            setTaskId(task_id);
        } catch {
            notifications.show({ color: "red", message: "Upload fehlgeschlagen." });
        }
    };

    // Poll task and redirect on success
    useEffect(() => {
        if (!taskId || !taskStatus.data) return;
        const { status } = taskStatus.data;
        if (status === "SUCCESS") {
            navigate(`/admin/vib-import/preview/${taskId}`);
        }
        if (status === "FAILURE") {
            notifications.show({
                color: "red",
                message: `Parser-Fehler: ${taskStatus.data.error ?? "Unbekannter Fehler"}`,
            });
            setTaskId(null);
        }
    }, [taskStatus.data, taskId, navigate]);

    const isParsing = taskId !== null && taskStatus.data?.status !== "SUCCESS";
    const progress =
        taskStatus.data?.status === "PROGRESS"
            ? (taskStatus.data.result as TaskProgressMeta | null)
            : null;

    const handleDeleteReport = (id: number, reportYear: number) => {
        modals.openConfirmModal({
            title: "VIB-Bericht löschen?",
            children: (
                <Text size="sm">
                    Der VIB-Bericht für Jahr {reportYear} wird unwiderruflich gelöscht.
                    Alle importierten Vorhaben gehen verloren.
                </Text>
            ),
            labels: { confirm: "Löschen", cancel: "Abbrechen" },
            confirmProps: { color: "red" },
            onConfirm: () =>
                deleteReport.mutate(id, {
                    onSuccess: () =>
                        notifications.show({ color: "green", message: "Bericht gelöscht." }),
                    onError: () =>
                        notifications.show({ color: "red", message: "Löschen fehlgeschlagen." }),
                }),
        });
    };

    return (
        <Container size="lg" py="xl">
            <Stack gap="xl">
                <ChronicleHeadline as="h1">VIB-Import (Verkehrsinvestitionsbericht)</ChronicleHeadline>

                {/* A — New import */}
                <ChronicleCard>
                    <Stack gap="md">
                        <Text fw={600} size="md">Neuer Import</Text>
                        <Text size="sm" c="dimmed">
                            PDF des Bundestagsdrucksache „Verkehrsinvestitionsbericht für das
                            Berichtsjahr XXXX" hochladen. Es wird nur Abschnitt B
                            (Schienenwege) importiert.
                        </Text>
                        <Group align="flex-end" gap="sm" wrap="wrap">
                            <FileInput
                                label="PDF-Datei (Verkehrsinvestitionsbericht)"
                                placeholder="PDF auswählen..."
                                accept="application/pdf"
                                value={file}
                                onChange={setFile}
                                w={380}
                            />
                            <NumberInput
                                label="Berichtsjahr"
                                value={year}
                                onChange={(v) => setYear(Number(v))}
                                min={2000}
                                max={2100}
                                w={120}
                            />
                        </Group>
                        <Group align="flex-end" gap="sm" wrap="wrap">
                            <NumberInput
                                label="OCR: von Seite (optional)"
                                description="Erste Seite von Abschnitt B"
                                placeholder="z. B. 45"
                                value={startPage}
                                onChange={(v) => setStartPage(v === "" ? "" : Number(v))}
                                min={1}
                                w={180}
                            />
                            <NumberInput
                                label="OCR: bis Seite (optional)"
                                description="Letzte Seite von Abschnitt B"
                                placeholder="z. B. 195"
                                value={endPage}
                                onChange={(v) => setEndPage(v === "" ? "" : Number(v))}
                                min={1}
                                w={180}
                            />
                            <Text size="xs" c="dimmed" maw={300} style={{ alignSelf: "flex-end", paddingBottom: 6 }}>
                                Seitenbereich einschränken, damit Mistral OCR nur Abschnitt B verarbeitet.
                                Leer lassen für automatische Erkennung.
                            </Text>
                        </Group>
                        <Group align="center" gap="xl">
                            <Checkbox
                                label="Kopf- und Fußzeilen ignorieren"
                                description="Wiederkehrende Zeilen (Seitenzahlen, Dokumenttitel) aus dem OCR-Text entfernen"
                                checked={stripHeadersFooters}
                                onChange={(e) => setStripHeadersFooters(e.currentTarget.checked)}
                            />
                            <Button
                                onClick={handleUpload}
                                loading={startImport.isPending || isParsing}
                                disabled={!file}
                            >
                                PDF parsen
                            </Button>
                        </Group>

                        {isParsing && (
                            <Stack gap={4}>
                                <Group gap="xs">
                                    <Loader size="xs" />
                                    <Text size="sm">
                                        {progress?.step_label
                                            ? progress.step_label
                                            : progress?.current_page != null
                                              ? `Seite ${progress.current_page} / ${progress.total_pages}`
                                              : "Parsing läuft…"}
                                    </Text>
                                </Group>
                                <Progress
                                    value={
                                        progress?.current_page != null && progress?.total_pages != null
                                            ? Math.round((progress.current_page / progress.total_pages) * 100)
                                            : 100
                                    }
                                    animated={!progress || progress.step === "ocr"}
                                    size="sm"
                                />
                            </Stack>
                        )}
                    </Stack>
                </ChronicleCard>

                {/* PDF preview — shown when a file is selected */}
                {pdfUrl && (
                    <ChronicleCard style={{ overflow: "hidden", padding: 0 }}>
                        <iframe
                            src={pdfUrl}
                            title="PDF-Vorschau"
                            style={{ width: "100%", height: "75vh", border: "none", display: "block" }}
                        />
                    </ChronicleCard>
                )}

                {/* B — Open drafts */}
                {(draftsLoading || (drafts && drafts.length > 0)) && (
                    <ChronicleCard>
                        <Stack gap="md">
                            <Text fw={600} size="md">Offene Entwürfe</Text>
                            <Text size="sm" c="dimmed">
                                Geparste PDFs, die noch nicht bestätigt wurden. Entwürfe können weiterbearbeitet werden.
                            </Text>
                            {draftsLoading ? (
                                <Group justify="center"><Loader /></Group>
                            ) : (
                                <Table striped highlightOnHover withTableBorder>
                                    <Table.Thead>
                                        <Table.Tr>
                                            <Table.Th>Jahr</Table.Th>
                                            <Table.Th>Erstellt</Table.Th>
                                            <Table.Th />
                                        </Table.Tr>
                                    </Table.Thead>
                                    <Table.Tbody>
                                        {drafts!.map((d) => (
                                            <Table.Tr key={d.task_id}>
                                                <Table.Td>{d.year}</Table.Td>
                                                <Table.Td>
                                                    {new Date(d.created_at).toLocaleString("de-DE", { timeZone: "Europe/Berlin" })}
                                                </Table.Td>
                                                <Table.Td>
                                                    <Group gap="xs" justify="flex-end">
                                                        <Button
                                                            size="xs"
                                                            variant="light"
                                                            onClick={() =>
                                                                navigate(`/admin/vib-import/review/${d.task_id}`)
                                                            }
                                                        >
                                                            Weiterbearbeiten
                                                        </Button>
                                                        <Button
                                                            size="xs"
                                                            variant="subtle"
                                                            color="red"
                                                            onClick={() =>
                                                                modals.openConfirmModal({
                                                                    title: "Entwurf verwerfen?",
                                                                    children: (
                                                                        <Text size="sm">
                                                                            Der Entwurf für Jahr {d.year} wird unwiderruflich gelöscht.
                                                                        </Text>
                                                                    ),
                                                                    labels: { confirm: "Verwerfen", cancel: "Abbrechen" },
                                                                    confirmProps: { color: "red" },
                                                                    onConfirm: () =>
                                                                        deleteDraft.mutate(d.task_id, {
                                                                            onError: () =>
                                                                                notifications.show({
                                                                                    color: "red",
                                                                                    message: "Löschen fehlgeschlagen.",
                                                                                }),
                                                                        }),
                                                                })
                                                            }
                                                        >
                                                            Verwerfen
                                                        </Button>
                                                    </Group>
                                                </Table.Td>
                                            </Table.Tr>
                                        ))}
                                    </Table.Tbody>
                                </Table>
                            )}
                        </Stack>
                    </ChronicleCard>
                )}

                {/* C — Imported reports */}
                <ChronicleCard>
                    <Stack gap="md">
                        <Text fw={600} size="md">Importierte Berichte</Text>
                        {reportsLoading ? (
                            <Group justify="center">
                                <Loader />
                            </Group>
                        ) : reports && reports.length > 0 ? (
                            <Table striped highlightOnHover withTableBorder>
                                <Table.Thead>
                                    <Table.Tr>
                                        <Table.Th>Jahr</Table.Th>
                                        <Table.Th>Drucksache</Table.Th>
                                        <Table.Th>Importiert</Table.Th>
                                        <Table.Th>Vorhaben</Table.Th>
                                        <Table.Th />
                                    </Table.Tr>
                                </Table.Thead>
                                <Table.Tbody>
                                    {reports.map((r) => (
                                        <Table.Tr key={r.id}>
                                            <Table.Td>{r.year}</Table.Td>
                                            <Table.Td>{r.drucksache_nr ?? "–"}</Table.Td>
                                            <Table.Td>
                                                {new Date(r.imported_at).toLocaleDateString(
                                                    "de-DE",
                                                    { timeZone: "Europe/Berlin" }
                                                )}
                                            </Table.Td>
                                            <Table.Td>{r.entry_count}</Table.Td>
                                            <Table.Td>
                                                <Button
                                                    size="xs"
                                                    variant="subtle"
                                                    color="red"
                                                    onClick={() =>
                                                        handleDeleteReport(r.id, r.year)
                                                    }
                                                >
                                                    Löschen
                                                </Button>
                                            </Table.Td>
                                        </Table.Tr>
                                    ))}
                                </Table.Tbody>
                            </Table>
                        ) : (
                            <Text size="sm" c="dimmed">
                                Noch keine VIB-Berichte importiert.
                            </Text>
                        )}
                    </Stack>
                </ChronicleCard>
            </Stack>
        </Container>
    );
}
