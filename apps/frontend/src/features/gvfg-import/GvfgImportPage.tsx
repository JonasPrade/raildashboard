import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Container, FileInput, Group, Paper, Stack, Table, Text, Title } from "@mantine/core";
import { openConfirmModal } from "../../shared/ui/confirmModal";
import { notifications } from "@mantine/notifications";
import { StatusTag } from "../../shared/ui/SwatchTag";
import RequirePermission from "../../components/RequirePermission";
import {
    useDeleteGvfgParseResult,
    useGvfgParseResults,
    useStartGvfgImport,
    type GvfgParseResultSummary,
} from "../../shared/api/queries";
import { exceedsUploadLimit, tooLargeMessage, uploadErrorMessage } from "../../shared/api/uploads";
import { formatDateTime } from "../../shared/format";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import { TaskProgressIndicator, useImportTask } from "../import-review/shared";
import { FileDropZone } from "../../shared/ui/FileDropZone";
import { LoadingState } from "../../shared/ui/LoadingState";

function edition(r: GvfgParseResultSummary): string {
    return r.year_from && r.year_to ? `${r.year_from}–${r.year_to}` : "–";
}

function ParseRuns({ results }: { results: GvfgParseResultSummary[] }) {
    const navigate = useNavigate();
    const deleteResult = useDeleteGvfgParseResult();

    const handleDelete = (r: GvfgParseResultSummary) =>
        openConfirmModal({
            title: "Import-Lauf löschen?",
            children: (
                <Text size="sm">
                    Der Lauf „{r.pdf_filename}“ wird gelöscht. Bereits übernommene Daten der Ausgabe bleiben
                    erhalten.
                </Text>
            ),
            labels: { confirm: "Löschen", cancel: "Abbrechen" },
            danger: true,
            onConfirm: async () => {
                try {
                    await deleteResult.mutateAsync(r.id);
                } catch {
                    notifications.show({ color: "red", message: "Löschen fehlgeschlagen." });
                }
            },
        });

    if (results.length === 0) {
        return <Text c="dimmed" size="sm">Noch keine Import-Läufe vorhanden.</Text>;
    }
    return (
        <ResponsiveTable minWidth={720} striped highlightOnHover withTableBorder>
            <Table.Thead>
                <Table.Tr>
                    <Table.Th>Ausgabe</Table.Th>
                    <Table.Th>Teil</Table.Th>
                    <Table.Th>Datei</Table.Th>
                    <Table.Th>Gelesen</Table.Th>
                    <Table.Th data-role="status">Status</Table.Th>
                    <Table.Th>Übernommen</Table.Th>
                    <Table.Th />
                </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
                {results.map((r) => (
                    <Table.Tr key={r.id}>
                        <Table.Td>{edition(r)}</Table.Td>
                        <Table.Td>{r.is_annex ? "Anhang" : "Hauptteil"}</Table.Td>
                        <Table.Td>{r.pdf_filename}</Table.Td>
                        <Table.Td>
                            {formatDateTime(r.parsed_at)}
                            {r.username_snapshot ? ` · ${r.username_snapshot}` : ""}
                        </Table.Td>
                        <Table.Td>
                            <StatusTag tone={r.status === "SUCCESS" ? "done" : "danger"}>{r.status === "SUCCESS" ? "gelesen" : "Fehler"}</StatusTag>
                        </Table.Td>
                        <Table.Td>{r.confirmed_at ? formatDateTime(r.confirmed_at) : "–"}</Table.Td>
                        <Table.Td>
                            <Group gap="xs" justify="flex-end" wrap="nowrap">
                                {r.status === "SUCCESS" && (
                                    <Button size="xs" variant="light" onClick={() => navigate(`/admin/gvfg-import/review/${r.id}`)}>
                                        {r.confirmed_at ? "Ansehen" : "Prüfen"}
                                    </Button>
                                )}
                                <Button size="xs" variant="subtle" color="red" onClick={() => handleDelete(r)}>
                                    Löschen
                                </Button>
                            </Group>
                        </Table.Td>
                    </Table.Tr>
                ))}
            </Table.Tbody>
        </ResponsiveTable>
    );
}

function GvfgImportPageContent() {
    const navigate = useNavigate();
    const [file, setFile] = useState<File | null>(null);
    const { data: results, isLoading } = useGvfgParseResults();
    const startImport = useStartGvfgImport();
    const task = useImportTask({
        onSuccess: (result) => {
            const id = (result as { parse_result_id?: number } | null)?.parse_result_id;
            if (id) navigate(`/admin/gvfg-import/review/${id}`);
        },
    });

    const handleUpload = async () => {
        if (!file) return;
        if (exceedsUploadLimit(file)) {
            notifications.show({ color: "red", title: "Datei zu groß", message: tooLargeMessage(file) });
            return;
        }
        try {
            const { task_id } = await startImport.mutateAsync(file);
            task.start(task_id);
        } catch (error) {
            notifications.show({ color: "red", message: uploadErrorMessage(error) });
        }
    };

    return (
        <Container size="lg" py="xl">
            <Stack gap="xl">
                <Title order={1}>GVFG-Import</Title>
                <Paper withBorder p="var(--card-pad)">
                    <Stack gap="md">
                        <Text fw={600}>Neuer Import</Text>
                        <Text size="sm" c="dimmed">
                            PDF des GVFG-Bundesprogramms (BMV, Referat E 22). Ein Anhang mit dem nachrichtlichen
                            Teil (z. B. 2024–2028) wird als eigene Datei hochgeladen und derselben Ausgabe
                            zugeordnet.
                        </Text>
                        <FileDropZone accept="application/pdf" onFiles={([dropped]) => setFile(dropped)} label="PDF hier ablegen">
                            <Group align="flex-end" gap="sm" wrap="wrap">
                                <FileInput
                                    label="PDF-Datei"
                                    placeholder="PDF auswählen oder hierher ziehen…"
                                    accept="application/pdf"
                                    value={file}
                                    onChange={setFile}
                                    w={320}
                                />
                                <Button onClick={handleUpload} loading={startImport.isPending || task.isRunning} disabled={!file}>
                                    PDF lesen
                                </Button>
                            </Group>
                        </FileDropZone>
                        {task.isRunning && <TaskProgressIndicator progress={task.progress} warning={task.warning} />}
                    </Stack>
                </Paper>
                <Paper withBorder p="var(--card-pad)">
                    <Stack gap="md">
                        <Text fw={600}>Import-Läufe</Text>
                        {isLoading ? <LoadingState rows={6} /> : <ParseRuns results={results ?? []} />}
                    </Stack>
                </Paper>
            </Stack>
        </Container>
    );
}

export default function GvfgImportPage() {
    return (
        <RequirePermission perm="gvfg.import">
            <GvfgImportPageContent />
        </RequirePermission>
    );
}
