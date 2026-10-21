import { useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
    Alert,
    Badge,
    Button,
    Container,
    Group,
    Loader,
    Paper,
    Stack,
    Text,
    Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { ArrowLeft, CheckCheck, Trash2 } from "lucide-react";

import {
    useConfirmFuldaYear,
    useDeleteFuldaYear,
    useFuldaEntries,
    useFuldaYearSummaries,
    useProjectOptions,
} from "../../shared/api/queries";
import { ANSWER_STATUS_LABEL, CATEGORY_ORDER, PhaseTable, bucketByCategory } from "./fuldaShared";

export default function FuldaYearDetailPage() {
    const navigate = useNavigate();
    const { year: yearParam } = useParams<{ year: string }>();
    const year = Number(yearParam);

    const { data: entries, isLoading } = useFuldaEntries(false, year);
    const { data: projects } = useProjectOptions();
    const { data: summaries } = useFuldaYearSummaries();
    const documents = summaries?.find((s) => s.announcement_year === year)?.documents ?? [];
    const deleteYear = useDeleteFuldaYear();
    const confirmYear = useConfirmFuldaYear();

    // Entries that have a project assigned but are not confirmed yet.
    const readyCount = useMemo(
        () => (entries ?? []).filter((e) => !e.confirmed && e.project_ids.length > 0).length,
        [entries],
    );

    const projectOptions = useMemo(
        () =>
            (projects ?? [])
                .filter((p) => p.id != null && p.name)
                .map((p) => ({
                    value: String(p.id),
                    label: p.superior_project_id ? `   ↳ ${p.name}` : (p.name as string),
                })),
        [projects],
    );

    const buckets = useMemo(() => bucketByCategory(entries ?? []), [entries]);
    const total = entries?.length ?? 0;

    const handleDeleteYear = () => {
        if (
            !window.confirm(
                `Wirklich alle ${total} Einträge der Fulda-Runde ${year} löschen? ` +
                    "Bestätigte Zuordnungen und deren Beobachtungen werden ebenfalls entfernt.",
            )
        ) {
            return;
        }
        deleteYear.mutate(year, {
            onSuccess: () => {
                notifications.show({
                    color: "green",
                    title: `Fulda-Runde ${year} gelöscht`,
                    message: `${total} Einträge entfernt.`,
                });
                navigate("/admin/fulda-import");
            },
            onError: () =>
                notifications.show({
                    color: "red",
                    title: "Fehler",
                    message: `Jahr ${year} konnte nicht gelöscht werden.`,
                }),
        });
    };

    const handleConfirmAll = () => {
        confirmYear.mutate(year, {
            onSuccess: (res) =>
                notifications.show({
                    color: "green",
                    title: "Übernommen",
                    message: `${res.confirmed} Einträge bestätigt — du kannst Zuordnungen weiterhin anpassen.`,
                }),
            onError: () =>
                notifications.show({
                    color: "red",
                    title: "Fehler",
                    message: "Die Einträge konnten nicht übernommen werden.",
                }),
        });
    };

    return (
        <Container size="xl" py="xl">
            <Stack gap="lg">
                <Group justify="space-between" align="flex-start">
                    <Stack gap={2}>
                        <Group gap="xs">
                            <Button
                                variant="subtle"
                                size="xs"
                                leftSection={<ArrowLeft size={16} />}
                                onClick={() => navigate("/admin/fulda-import")}
                            >
                                Übersicht
                            </Button>
                        </Group>
                        <Group gap="xs">
                            <Title order={2}>Fulda-Runde {year}</Title>
                            <Badge variant="light">{total} Einträge</Badge>
                        </Group>
                    </Stack>
                    <Group gap="sm">
                        <Button
                            color="green"
                            leftSection={<CheckCheck size={16} />}
                            onClick={handleConfirmAll}
                            loading={confirmYear.isPending}
                            disabled={readyCount === 0}
                            title={
                                readyCount === 0
                                    ? "Keine zugeordneten, offenen Einträge"
                                    : "Alle zugeordneten Einträge übernehmen"
                            }
                        >
                            Alle übernehmen{readyCount > 0 ? ` (${readyCount})` : ""}
                        </Button>
                        <Button
                            color="red"
                            variant="light"
                            leftSection={<Trash2 size={16} />}
                            onClick={handleDeleteYear}
                            loading={deleteYear.isPending}
                        >
                            Jahr löschen
                        </Button>
                    </Group>
                </Group>

                {isLoading ? (
                    <Group justify="center" py="xl">
                        <Loader />
                    </Group>
                ) : null}

                {documents.map((d) => (
                    <Paper key={d.id} withBorder p="sm" radius="md">
                        <Stack gap={4}>
                            <Group gap="xs">
                                <Text fw={600} size="sm">
                                    Drs. {d.drucksache}
                                </Text>
                                <Text size="sm" c="dimmed">
                                    vom {new Date(d.document_date).toLocaleDateString("de-DE")}
                                </Text>
                                <Badge
                                    variant="light"
                                    color={d.answer_status === "VOLLSTAENDIG" ? "green" : "orange"}
                                >
                                    {ANSWER_STATUS_LABEL[d.answer_status]}
                                </Badge>
                            </Group>
                            {d.title && <Text size="sm">{d.title}</Text>}
                            {d.note && (
                                <Text size="sm" c="dimmed">
                                    {d.note}
                                </Text>
                            )}
                        </Stack>
                    </Paper>
                ))}

                {isLoading ? null : total === 0 ? (
                    <Alert variant="light" title="Keine Einträge">
                        Für {year} liegen keine Fulda-Einträge vor.
                    </Alert>
                ) : (
                    <Stack gap="xl">
                        {/* Only categories the answer actually lists. */}
                        {CATEGORY_ORDER.filter((cat) => (buckets.map.get(cat) ?? []).length > 0).map(
                            (cat) => (
                                <PhaseTable
                                    key={cat}
                                    category={cat}
                                    rows={buckets.map.get(cat) ?? []}
                                    projectOptions={projectOptions}
                                />
                            ),
                        )}
                        {buckets.other.length > 0 && (
                            <PhaseTable
                                category="Ohne Kategorie"
                                rows={buckets.other}
                                projectOptions={projectOptions}
                            />
                        )}
                    </Stack>
                )}
            </Stack>
        </Container>
    );
}
