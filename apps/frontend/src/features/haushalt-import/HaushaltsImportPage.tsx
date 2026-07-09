import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
    Anchor,
    Button,
    Container,
    FileInput,
    Group,
    Loader,
    NumberInput,
    Stack,
    Text,
} from "@mantine/core";
import { ChronicleHeadline, ChronicleCard } from "../../components/chronicle";
import { notifications } from "@mantine/notifications";
import RequirePermission from "../../components/RequirePermission";
import {
    useParseResults,
    useStartHaushaltsImport,
} from "../../shared/api/queries";
import { TaskProgressIndicator, useImportTask } from "../import-review/shared";
import { ParseResultList } from "./components/ParseResultList";

function HaushaltsImportPageContent() {
    const navigate = useNavigate();

    const [file, setFile] = useState<File | null>(null);
    const [year, setYear] = useState<number>(new Date().getFullYear());

    const { data: results, isLoading: resultsLoading } = useParseResults();
    const startImport = useStartHaushaltsImport();
    const task = useImportTask({
        onSuccess: (result) => {
            const parseResultId = (result as { parse_result_id?: number } | null)?.parse_result_id;
            if (parseResultId) {
                navigate(`/admin/haushalt-import/review/${parseResultId}`);
            }
        },
    });

    const handleUpload = async () => {
        if (!file) return;
        try {
            const { task_id } = await startImport.mutateAsync({ pdf: file, year });
            task.start(task_id);
        } catch {
            notifications.show({ color: "red", message: "Upload fehlgeschlagen." });
        }
    };

    const isParsing = task.isRunning;
    const progress = task.progress;

    return (
        <Container size="lg" py="xl">
            <Stack gap="xl">
                <Group justify="space-between" align="center">
                    <ChronicleHeadline as="h1">Haushalts-Import</ChronicleHeadline>
                    <Anchor component={Link} to="/admin/haushalt-import/guide" size="sm">
                        Anleitung anzeigen →
                    </Anchor>
                </Group>

                {/* A — New import */}
                <ChronicleCard>
                    <Stack gap="md">
                        <Text fw={600} size="md">Neuer Import</Text>
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
                            <TaskProgressIndicator
                                progress={progress}
                                label={
                                    progress?.current_page != null
                                        ? `Seite ${progress.current_page} / ${progress.total_pages} — ${progress.rows_found} Zeilen gefunden`
                                        : undefined
                                }
                            />
                        )}
                    </Stack>
                </ChronicleCard>

                {/* B — Existing results */}
                <ChronicleCard>
                    <Stack gap="md">
                        <Text fw={600} size="md">Vergangene Import-Läufe</Text>
                        {resultsLoading ? (
                            <Group justify="center"><Loader /></Group>
                        ) : (
                            <ParseResultList results={results ?? []} />
                        )}
                    </Stack>
                </ChronicleCard>
            </Stack>
        </Container>
    );
}

export default function HaushaltsImportPage() {
    return (
        <RequirePermission perm="haushalt.import">
            <HaushaltsImportPageContent />
        </RequirePermission>
    );
}
