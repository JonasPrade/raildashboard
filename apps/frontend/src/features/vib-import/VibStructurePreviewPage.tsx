import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
    Alert,
    Badge,
    Button,
    Container,
    Group,
    Loader,
    Paper,
    Progress,
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
    useVibAiAvailable,
    useStartVibAiExtraction,
    useTaskStatus,
} from "../../shared/api/queries";

const CATEGORY_COLORS: Record<string, string> = {
    laufend: "blue",
    neu: "green",
    potentiell: "yellow",
    abgeschlossen: "gray",
};

export default function VibStructurePreviewPage() {
    const { taskId } = useParams<{ taskId: string }>();
    const navigate = useNavigate();
    const { user } = useAuth();

    const { data: parseResult, isLoading, isError } = useVibParseResult(taskId ?? null);
    const { data: aiAvailable } = useVibAiAvailable();
    const startAiExtraction = useStartVibAiExtraction();

    const [aiTaskId, setAiTaskId] = useState<string | null>(null);
    const aiTaskStatus = useTaskStatus(aiTaskId);

    useEffect(() => {
        if (!aiTaskId || !aiTaskStatus.data) return;
        const { status } = aiTaskStatus.data;
        if (status === "SUCCESS") {
            navigate(`/admin/vib-import/review/${taskId}`);
        }
        if (status === "FAILURE") {
            notifications.show({
                color: "red",
                message: `KI-Extraktion fehlgeschlagen: ${aiTaskStatus.data.error ?? "Unbekannter Fehler"}`,
            });
            setAiTaskId(null);
        }
    }, [aiTaskStatus.data, aiTaskId, navigate, taskId]);

    if (user?.role !== "editor" && user?.role !== "admin") {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Kein Zugriff">
                    Diese Seite ist nur für Editoren und Administratoren zugänglich.
                </Alert>
            </Container>
        );
    }

    const handleStartAi = async () => {
        if (!taskId) return;
        try {
            const { task_id } = await startAiExtraction.mutateAsync(taskId);
            setAiTaskId(task_id);
        } catch {
            notifications.show({ color: "red", message: "KI-Extraktion konnte nicht gestartet werden." });
        }
    };

    if (isLoading) {
        return (
            <Container py="xl">
                <Group justify="center"><Loader /></Group>
            </Container>
        );
    }

    if (isError || !parseResult) {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Fehler">
                    Parse-Ergebnis konnte nicht geladen werden.
                </Alert>
            </Container>
        );
    }

    const entries = parseResult.entries;
    const withoutPfa = entries.filter((e) => e.pfa_entries.length === 0);
    const isAiRunning = aiTaskId !== null && aiTaskStatus.data?.status !== "SUCCESS";
    const aiProgress =
        aiTaskStatus.data?.status === "PROGRESS"
            ? (aiTaskStatus.data.result as { current: number; total: number } | null)
            : null;

    return (
        <Container size="lg" py="xl">
            <Stack gap="xl">
                <div>
                    <Title order={2}>VIB-Import — Strukturvorschau</Title>
                    <Text c="dimmed" size="sm" mt={4}>
                        Schritt 1 abgeschlossen. Prüfen Sie die erkannte Struktur, bevor die
                        KI-Extraktion gestartet wird.
                    </Text>
                </div>

                <Paper withBorder p="md">
                    <Group gap="xl">
                        <div>
                            <Text size="xs" c="dimmed">Projekte erkannt</Text>
                            <Text fw={700} size="xl">{entries.length}</Text>
                        </div>
                        <div>
                            <Text size="xs" c="dimmed">Berichtsjahr</Text>
                            <Text fw={700} size="xl">{parseResult.year}</Text>
                        </div>
                        <div>
                            <Text size="xs" c="dimmed">Drucksache</Text>
                            <Text fw={700} size="xl">{parseResult.drucksache_nr ?? "–"}</Text>
                        </div>
                    </Group>
                </Paper>

                {withoutPfa.length > 0 && (
                    <Alert color="yellow" variant="light" title="Hinweis">
                        {withoutPfa.length} Projekt{withoutPfa.length > 1 ? "e" : ""} ohne
                        PFA-Tabelle erkannt. Das kann auf Parsing-Probleme hinweisen.
                    </Alert>
                )}

                <Paper withBorder p={0}>
                    <Table withTableBorder highlightOnHover>
                        <Table.Thead>
                            <Table.Tr>
                                <Table.Th>Sektion</Table.Th>
                                <Table.Th>Projektname</Table.Th>
                                <Table.Th>Kategorie</Table.Th>
                                <Table.Th>PFA-Zeilen</Table.Th>
                                <Table.Th>Vorschau Rohtext</Table.Th>
                            </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                            {entries.map((e, idx) => (
                                <Table.Tr key={idx}>
                                    <Table.Td>
                                        <Text size="xs" ff="monospace">{e.vib_section ?? "–"}</Text>
                                    </Table.Td>
                                    <Table.Td>
                                        <Text size="sm" lineClamp={2}>{e.vib_name_raw}</Text>
                                    </Table.Td>
                                    <Table.Td>
                                        <Badge size="xs" color={CATEGORY_COLORS[e.category] ?? "gray"}>
                                            {e.category}
                                        </Badge>
                                    </Table.Td>
                                    <Table.Td>
                                        <Text size="sm" c={e.pfa_entries.length === 0 ? "orange" : undefined}>
                                            {e.pfa_entries.length}
                                        </Text>
                                    </Table.Td>
                                    <Table.Td>
                                        <Text size="xs" c="dimmed" ff="monospace" lineClamp={1}>
                                            {(e.raw_text ?? "–").slice(0, 120)}
                                        </Text>
                                    </Table.Td>
                                </Table.Tr>
                            ))}
                        </Table.Tbody>
                    </Table>
                </Paper>

                {isAiRunning && (
                    <Stack gap={4}>
                        <Group gap="xs">
                            <Loader size="xs" />
                            <Text size="sm">
                                {aiProgress
                                    ? `KI-Extraktion: Projekt ${aiProgress.current} / ${aiProgress.total}`
                                    : "KI-Extraktion läuft…"}
                            </Text>
                        </Group>
                        <Progress
                            value={
                                aiProgress
                                    ? Math.round((aiProgress.current / aiProgress.total) * 100)
                                    : 100
                            }
                            animated={!aiProgress}
                            size="sm"
                        />
                    </Stack>
                )}

                <Group justify="flex-end" gap="sm">
                    <Button variant="subtle" onClick={() => navigate("/admin/vib-import")}>
                        Abbrechen
                    </Button>
                    <Button
                        variant="default"
                        onClick={() => navigate(`/admin/vib-import/review/${taskId}`)}
                        disabled={isAiRunning}
                    >
                        Ohne KI weiter →
                    </Button>
                    <Tooltip
                        label={
                            !aiAvailable?.available
                                ? "LLM nicht konfiguriert (LLM_BASE_URL fehlt)"
                                : `Modell: ${aiAvailable.model}`
                        }
                        disabled={aiAvailable?.available}
                    >
                        <Button
                            onClick={handleStartAi}
                            loading={isAiRunning || startAiExtraction.isPending}
                            disabled={!aiAvailable?.available || isAiRunning}
                        >
                            Weiter mit KI-Extraktion →
                        </Button>
                    </Tooltip>
                </Group>
            </Stack>
        </Container>
    );
}
