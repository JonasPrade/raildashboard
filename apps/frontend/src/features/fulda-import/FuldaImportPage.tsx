import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
    Alert,
    Badge,
    Button,
    Container,
    FileInput,
    Group,
    Loader,
    Paper,
    Stack,
    Table,
    Text,
    Title,
    NumberInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconChevronRight, IconUpload } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";

import {
    type FuldaParseSummary,
    useFuldaYearSummaries,
    useParseFulda,
    useTaskStatus,
    queryKeys,
} from "../../shared/api/queries";

export default function FuldaImportPage() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [file, setFile] = useState<File | null>(null);
    const [importYear, setImportYear] = useState<number>(new Date().getFullYear());
    const [taskId, setTaskId] = useState<string | null>(null);

    const { data: summaries, isLoading } = useFuldaYearSummaries();
    const parse = useParseFulda();
    const { data: taskStatus } = useTaskStatus(taskId);

    const handleParse = () => {
        if (!file) return;
        parse.mutate(
            { file, year: importYear },
            {
                onSuccess: (launch) => setTaskId(launch.task_id),
                onError: () =>
                    notifications.show({
                        color: "red",
                        title: "Auswertung fehlgeschlagen",
                        message: "Das PDF konnte nicht hochgeladen werden.",
                    }),
            },
        );
    };

    // OCR + LLM run in a Celery task — react once it finishes.
    useEffect(() => {
        if (!taskId || !taskStatus) return;
        if (taskStatus.status === "SUCCESS") {
            const summary = taskStatus.result as FuldaParseSummary | null;
            setTaskId(null);
            setFile(null);
            queryClient.invalidateQueries({ queryKey: queryKeys.fuldaEntries });
            queryClient.invalidateQueries({ queryKey: queryKeys.fuldaYears });
            queryClient.invalidateQueries({ queryKey: queryKeys.fuldaYearSummaries });
            notifications.show({
                color: "green",
                title: `Fulda-Runde ${importYear} ausgewertet`,
                message: summary
                    ? `${summary.created} Einträge erkannt (OCR: ${summary.ocr_status}) — bitte prüfen.`
                    : "Auswertung abgeschlossen — bitte prüfen.",
            });
            navigate(`/admin/fulda-import/year/${importYear}`);
        } else if (taskStatus.status === "FAILURE") {
            setTaskId(null);
            notifications.show({
                color: "red",
                title: "Auswertung fehlgeschlagen",
                message: taskStatus.error ?? "Das PDF konnte nicht verarbeitet werden.",
            });
        }
    }, [taskId, taskStatus, importYear, navigate, queryClient]);

    const isParsing = parse.isPending || taskId !== null;

    return (
        <Container size="lg" py="xl">
            <Stack gap="lg">
                <Stack gap={4}>
                    <Title order={2}>Fulda-Runde</Title>
                    <Text c="dimmed" size="sm">
                        <b>Antwort der Bundesregierung</b> auf die Kleine Anfrage zur „Fulda-Runde"
                        (PDF) hochladen — nicht die Anfrage selbst, denn nur die Antwort enthält die
                        Projektlisten. OCR + KI ordnen jede Projektliste anhand der Frage-Überschrift
                        einer Leistungsphase zu (inkl. Abschnitt → Unterprojekt). Anschließend wird
                        der Jahrgang <b>Schritt für Schritt</b> durchgearbeitet; bestätigte
                        Zuordnungen erzeugen je Projekt eine Beobachtung (Quelle „Fulda-Runde").
                    </Text>
                </Stack>

                {/* Upload */}
                <Paper withBorder p="md" radius="md">
                    <Group align="flex-end">
                        <NumberInput
                            label="Fulda-Runde Jahr"
                            value={importYear}
                            onChange={(v) => setImportYear(Number(v))}
                            min={2000}
                            max={2100}
                            allowDecimal={false}
                            w={140}
                        />
                        <FileInput
                            label="Antwort der Bundesregierung (PDF)"
                            placeholder="PDF auswählen"
                            accept="application/pdf"
                            value={file}
                            onChange={setFile}
                            leftSection={<IconUpload size={16} />}
                            style={{ flex: 1, maxWidth: 420 }}
                        />
                        <Button onClick={handleParse} loading={isParsing} disabled={!file}>
                            Auswerten & durcharbeiten
                        </Button>
                    </Group>
                    {isParsing && (
                        <Text size="sm" c="dimmed" mt="xs">
                            OCR und KI-Auswertung laufen im Hintergrund — das kann bei großen
                            PDFs einige Minuten dauern. Die Seite bleibt benutzbar.
                        </Text>
                    )}
                </Paper>

                {/* Year overview table */}
                <Stack gap="xs">
                    <Title order={4}>Jahrgänge</Title>
                    {isLoading ? (
                        <Group justify="center" py="xl">
                            <Loader />
                        </Group>
                    ) : !summaries || summaries.length === 0 ? (
                        <Alert variant="light" title="Keine Jahrgänge">
                            Noch keine Fulda-Einträge. Lade oben eine Antwort der Bundesregierung hoch.
                        </Alert>
                    ) : (
                        <Table striped highlightOnHover>
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>Jahr</Table.Th>
                                    <Table.Th>Drucksache</Table.Th>
                                    <Table.Th>Einträge</Table.Th>
                                    <Table.Th>Status</Table.Th>
                                    <Table.Th />
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {summaries.map((s) => {
                                    const open = s.total - s.confirmed;
                                    return (
                                        <Table.Tr
                                            key={s.announcement_year}
                                            style={{ cursor: "pointer" }}
                                            onClick={() =>
                                                navigate(`/admin/fulda-import/year/${s.announcement_year}`)
                                            }
                                        >
                                            <Table.Td>
                                                <Text fw={600}>{s.announcement_year}</Text>
                                            </Table.Td>
                                            <Table.Td>
                                                <Text size="sm" c="dimmed">
                                                    {s.source_label ?? "—"}
                                                </Text>
                                            </Table.Td>
                                            <Table.Td>{s.total}</Table.Td>
                                            <Table.Td>
                                                <Group gap="xs">
                                                    <Badge variant="light" color="green">
                                                        {s.confirmed} aktiv
                                                    </Badge>
                                                    {open > 0 && (
                                                        <Badge variant="light" color="orange">
                                                            {open} offen
                                                        </Badge>
                                                    )}
                                                </Group>
                                            </Table.Td>
                                            <Table.Td onClick={(e) => e.stopPropagation()}>
                                                <Group gap="xs" justify="flex-end" wrap="nowrap">
                                                    <Button
                                                        size="xs"
                                                        variant="light"
                                                        rightSection={<IconChevronRight size={14} />}
                                                        onClick={() =>
                                                            navigate(
                                                                `/admin/fulda-import/year/${s.announcement_year}`,
                                                            )
                                                        }
                                                    >
                                                        Öffnen
                                                    </Button>
                                                </Group>
                                            </Table.Td>
                                        </Table.Tr>
                                    );
                                })}
                            </Table.Tbody>
                        </Table>
                    )}
                </Stack>
            </Stack>
        </Container>
    );
}
