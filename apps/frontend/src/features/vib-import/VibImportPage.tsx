import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
    Alert,
    Button,
    Container,
    FileInput,
    Group,
    Loader,
    NumberInput,
    Paper,
    Progress,
    Stack,
    Table,
    Text,
    Title,
} from "@mantine/core";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import { useAuth } from "../../lib/auth";
import {
    useStartVibImport,
    useTaskStatus,
    useVibReports,
    useDeleteVibReport,
    type TaskProgressMeta,
} from "../../shared/api/queries";

export default function VibImportPage() {
    const { user } = useAuth();
    const navigate = useNavigate();

    const [file, setFile] = useState<File | null>(null);
    const [year, setYear] = useState<number>(new Date().getFullYear() - 1);
    const [taskId, setTaskId] = useState<string | null>(null);

    const startImport = useStartVibImport();
    const taskStatus = useTaskStatus(taskId);
    const { data: reports, isLoading: reportsLoading } = useVibReports();
    const deleteReport = useDeleteVibReport();

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
            const { task_id } = await startImport.mutateAsync({ pdf: file, year });
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
            navigate(`/admin/vib-import/review/${taskId}`);
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
                <Title order={2}>VIB-Import (Verkehrsinvestitionsbericht)</Title>

                {/* A — New import */}
                <Paper withBorder p="md">
                    <Stack gap="md">
                        <Title order={4}>Neuer Import</Title>
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
                                        {progress
                                            ? `Seite ${progress.current_page} / ${progress.total_pages}`
                                            : "Parsing läuft…"}
                                    </Text>
                                </Group>
                                <Progress
                                    value={
                                        progress
                                            ? Math.round(
                                                  (progress.current_page / progress.total_pages) *
                                                      100
                                              )
                                            : 100
                                    }
                                    animated={!progress}
                                    size="sm"
                                />
                            </Stack>
                        )}
                    </Stack>
                </Paper>

                {/* B — Imported reports */}
                <Paper withBorder p="md">
                    <Stack gap="md">
                        <Title order={4}>Importierte Berichte</Title>
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
                                                    "de-DE"
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
                </Paper>
            </Stack>
        </Container>
    );
}
