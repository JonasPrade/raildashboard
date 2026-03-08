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
    Text,
    Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useAuth } from "../../lib/auth";
import {
    useParseResults,
    useStartHaushaltsImport,
    useTaskStatus,
    type TaskProgressMeta,
} from "../../shared/api/queries";
import { ParseResultList } from "./components/ParseResultList";

export default function HaushaltsImportPage() {
    const { user } = useAuth();
    const navigate = useNavigate();

    const [file, setFile] = useState<File | null>(null);
    const [year, setYear] = useState<number>(new Date().getFullYear());
    const [taskId, setTaskId] = useState<string | null>(null);

    const { data: results, isLoading: resultsLoading } = useParseResults();
    const startImport = useStartHaushaltsImport();
    const taskStatus = useTaskStatus(taskId);

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
        const { status, result } = taskStatus.data;
        if (status === "SUCCESS" && result) {
            const parseResultId = (result as { parse_result_id?: number }).parse_result_id;
            if (parseResultId) {
                navigate(`/admin/haushalt-import/review/${parseResultId}`);
            }
        }
        if (status === "FAILURE") {
            notifications.show({ color: "red", message: `Parser-Fehler: ${taskStatus.data.error}` });
            setTaskId(null);
        }
    }, [taskStatus.data, taskId, navigate]);

    const isParsing = taskId !== null && taskStatus.data?.status !== "SUCCESS";
    const progress = taskStatus.data?.status === "PROGRESS"
        ? (taskStatus.data.result as TaskProgressMeta | null)
        : null;

    return (
        <Container size="lg" py="xl">
            <Stack gap="xl">
                <Title order={2}>Haushalts-Import</Title>

                {/* A — New import */}
                <Paper withBorder p="md">
                    <Stack gap="md">
                        <Title order={4}>Neuer Import</Title>
                        <Group align="flex-end" gap="sm" wrap="wrap">
                            <FileInput
                                label="PDF-Datei (Anlage VWIB Teil B)"
                                placeholder="PDF auswählen..."
                                accept="application/pdf"
                                value={file}
                                onChange={setFile}
                                w={320}
                            />
                            <NumberInput
                                label="Haushaltsjahr"
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
                                            ? `Seite ${progress.current_page} / ${progress.total_pages} — ${progress.rows_found} Zeilen gefunden`
                                            : "Parsing läuft…"}
                                    </Text>
                                </Group>
                                <Progress
                                    value={progress
                                        ? Math.round((progress.current_page / progress.total_pages) * 100)
                                        : 100}
                                    animated={!progress}
                                    size="sm"
                                />
                            </Stack>
                        )}
                    </Stack>
                </Paper>

                {/* B — Existing results */}
                <Paper withBorder p="md">
                    <Stack gap="md">
                        <Title order={4}>Vergangene Import-Läufe</Title>
                        {resultsLoading ? (
                            <Group justify="center"><Loader /></Group>
                        ) : (
                            <ParseResultList results={results ?? []} />
                        )}
                    </Stack>
                </Paper>
            </Stack>
        </Container>
    );
}
