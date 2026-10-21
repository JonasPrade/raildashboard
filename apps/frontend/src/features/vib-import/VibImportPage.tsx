import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
    Button,
    Checkbox,
    Container,
    FileInput,
    Group,
    NumberInput,
    Paper,
    Stack,
    Table,
    Text,
    Title,
} from "@mantine/core";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import RequirePermission from "../../components/RequirePermission";
import {
    useStartVibImport,
    useVibReports,
    useDeleteVibReport,
    useVibDrafts,
    useDeleteVibDraft,
} from "../../shared/api/queries";
import { exceedsUploadLimit, tooLargeMessage, uploadErrorMessage } from "../../shared/api/uploads";
import { TaskProgressIndicator, useImportTask } from "../import-review/shared";
import { formatDateNumeric, formatDateTime } from "../../shared/format";
import { FileDropZone } from "../../shared/ui/FileDropZone";
import { LoadingState } from "../../shared/ui/LoadingState";

function VibImportPageContent() {
    const navigate = useNavigate();

    const [file, setFile] = useState<File | null>(null);
    const [pdfUrl, setPdfUrl] = useState<string | null>(null);
    const [year, setYear] = useState<number>(new Date().getFullYear() - 1);
    const [startPage, setStartPage] = useState<number | "">("");
    const [endPage, setEndPage] = useState<number | "">("");
    const [stripHeadersFooters, setStripHeadersFooters] = useState(true);

    useEffect(() => {
        if (!file) { setPdfUrl(null); return; }
        const url = URL.createObjectURL(file);
        setPdfUrl(url);
        return () => URL.revokeObjectURL(url);
    }, [file]);

    const startImport = useStartVibImport();
    const task = useImportTask({
        onSuccess: (_result, finishedTaskId) => {
            navigate(`/admin/vib-import/preview/${finishedTaskId}`);
        },
    });
    const { data: reports, isLoading: reportsLoading } = useVibReports();
    const deleteReport = useDeleteVibReport();
    const { data: drafts, isLoading: draftsLoading } = useVibDrafts();
    const deleteDraft = useDeleteVibDraft();

    const handleUpload = async () => {
        if (!file) return;
        if (exceedsUploadLimit(file)) {
            notifications.show({ color: "red", title: "Datei zu groß", message: tooLargeMessage(file) });
            return;
        }
        try {
            const { task_id } = await startImport.mutateAsync({
                pdf: file,
                year,
                startPage: startPage !== "" ? startPage : undefined,
                endPage: endPage !== "" ? endPage : undefined,
                stripHeadersFooters,
            });
            task.start(task_id);
        } catch (error) {
            notifications.show({ color: "red", message: uploadErrorMessage(error) });
        }
    };

    const isParsing = task.isRunning;
    const progress = task.progress;

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
                <Title order={1}>VIB-Import (Verkehrsinvestitionsbericht)</Title>

                {/* A — New import */}
                <Paper withBorder p="var(--card-pad)">
                    <Stack gap="md">
                        <Text fw={600} size="md">Neuer Import</Text>
                        <Text size="sm" c="dimmed">
                            PDF des Bundestagsdrucksache „Verkehrsinvestitionsbericht für das
                            Berichtsjahr XXXX" hochladen. Es wird nur Abschnitt B
                            (Schienenwege) importiert.
                        </Text>
                        <FileDropZone accept="application/pdf" onFiles={([dropped]) => setFile(dropped)} label="PDF hier ablegen">
                            <Group align="flex-end" gap="sm" wrap="wrap">
                                <FileInput
                                    label="PDF-Datei (Verkehrsinvestitionsbericht)"
                                    placeholder="PDF auswählen oder hierher ziehen…"
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
                        </FileDropZone>
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
                            <TaskProgressIndicator
                                progress={progress}
                                animated={!progress || progress.step === "ocr"}
                                warning={task.warning}
                            />
                        )}
                    </Stack>
                </Paper>

                {/* PDF preview — shown when a file is selected */}
                {pdfUrl && (
                    <Paper withBorder p={0} style={{ overflow: "hidden" }}>
                        <iframe
                            src={pdfUrl}
                            title="PDF-Vorschau"
                            style={{ width: "100%", height: "75vh", border: "none", display: "block" }}
                        />
                    </Paper>
                )}

                {/* B — Open drafts */}
                {(draftsLoading || (drafts && drafts.length > 0)) && (
                    <Paper withBorder p="var(--card-pad)">
                        <Stack gap="md">
                            <Text fw={600} size="md">Offene Entwürfe</Text>
                            <Text size="sm" c="dimmed">
                                Geparste PDFs, die noch nicht bestätigt wurden. Entwürfe können weiterbearbeitet werden.
                            </Text>
                            {draftsLoading ? (
                                <LoadingState rows={6} />
                            ) : (
                                <ResponsiveTable minWidth={720} striped highlightOnHover withTableBorder>
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
                                                    {formatDateTime(d.created_at)}
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
                                </ResponsiveTable>
                            )}
                        </Stack>
                    </Paper>
                )}

                {/* C — Imported reports */}
                <Paper withBorder p="var(--card-pad)">
                    <Stack gap="md">
                        <Text fw={600} size="md">Importierte Berichte</Text>
                        {reportsLoading ? (
                            <LoadingState rows={6} />
                        ) : reports && reports.length > 0 ? (
                            <ResponsiveTable minWidth={720} striped highlightOnHover withTableBorder>
                                <Table.Thead>
                                    <Table.Tr>
                                        <Table.Th>Jahr</Table.Th>
                                        <Table.Th>Drucksache</Table.Th>
                                        <Table.Th>Importiert</Table.Th>
                                        <Table.Th className="num">Vorhaben</Table.Th>
                                        <Table.Th />
                                    </Table.Tr>
                                </Table.Thead>
                                <Table.Tbody>
                                    {reports.map((r) => (
                                        <Table.Tr key={r.id}>
                                            <Table.Td>{r.year}</Table.Td>
                                            <Table.Td>{r.drucksache_nr ?? "–"}</Table.Td>
                                            <Table.Td>
                                                {formatDateNumeric(r.imported_at)}
                                            </Table.Td>
                                            <Table.Td className="num">{r.entry_count}</Table.Td>
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
                            </ResponsiveTable>
                        ) : (
                            <Text size="sm" c="dimmed">
                                Noch keine VIB-Berichte importiert.
                            </Text>
                        )}
                    </Stack>
                </Paper>
            </Stack>
        </Container>
    );
}

export default function VibImportPage() {
    return (
        <RequirePermission perm="vib.import">
            <VibImportPageContent />
        </RequirePermission>
    );
}
