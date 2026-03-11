import { Link, useNavigate, useParams } from "react-router-dom";
import { useState } from "react";
import {
    Alert,
    Anchor,
    Badge,
    Button,
    Container,
    Group,
    Loader,
    Stack,
    Text,
    Title,
} from "@mantine/core";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import { useAuth } from "../../lib/auth";
import {
    useParseResult,
    useProjects,
    useConfirmHaushaltsImport,
    useDeleteParseResult,
    type HaushaltsParseRow,
} from "../../shared/api/queries";
import { ReviewTable } from "./components/ReviewTable";

export default function HaushaltsReviewPage() {
    const { parseResultId } = useParams<{ parseResultId: string }>();
    const id = Number(parseResultId);

    const navigate = useNavigate();
    const { user } = useAuth();
    const { data: result, isLoading, isError } = useParseResult(id);
    const { data: projects } = useProjects();
    const confirm = useConfirmHaushaltsImport();
    const deleteResult = useDeleteParseResult();

    const [rows, setRows] = useState<HaushaltsParseRow[] | null>(null);

    if (user?.role !== "editor" && user?.role !== "admin") {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Kein Zugriff">
                    Diese Seite ist nur für Editoren und Administratoren zugänglich.
                </Alert>
            </Container>
        );
    }

    if (isLoading) return <Container py="xl"><Group justify="center"><Loader /></Group></Container>;
    if (isError || !result) {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Fehler">
                    Parse-Ergebnis konnte nicht geladen werden.
                </Alert>
            </Container>
        );
    }

    const displayRows: HaushaltsParseRow[] = rows ?? (result.result_json?.rows ?? []);
    const isConfirmed = result.confirmed_at !== null;

    const handleProjectIdsChange = (finveNumber: number, projectIds: number[]) => {
        setRows((prev) => {
            const base = prev ?? (result.result_json?.rows ?? []);
            return base.map((r) =>
                r.finve_number === finveNumber ? { ...r, project_ids: projectIds } : r
            );
        });
    };

    const handleDiscard = () => {
        modals.openConfirmModal({
            title: "Parse-Ergebnis verwerfen?",
            children: (
                <Text size="sm">
                    Der Parse-Lauf für Haushalt {result?.haushalt_year} wird gelöscht.
                    Es wurden noch keine Daten importiert.
                </Text>
            ),
            labels: { confirm: "Verwerfen", cancel: "Abbrechen" },
            confirmProps: { color: "red" },
            onConfirm: async () => {
                try {
                    await deleteResult.mutateAsync(id);
                    navigate("/admin/haushalt-import");
                } catch {
                    notifications.show({ color: "red", message: "Verwerfen fehlgeschlagen." });
                }
            },
        });
    };

    const handleConfirm = async () => {
        try {
            const resp = await confirm.mutateAsync({
                parse_result_id: id,
                rows: displayRows,
                unmatched_action: "save",
            });
            notifications.show({
                color: "green",
                title: "Import abgeschlossen",
                message: `${resp.finves_created} FinVes neu, ${resp.finves_updated} aktualisiert. ${resp.unmatched_saved} unbekannte Zeilen gespeichert.`,
                autoClose: 8000,
            });
            navigate("/admin/haushalt-import");
        } catch (e: unknown) {
            const detail = (e as { details?: { detail?: string } })?.details?.detail;
            notifications.show({
                color: "red",
                message: detail ?? "Import fehlgeschlagen.",
            });
        }
    };

    return (
        <Container size="xl" py="xl">
            <Stack gap="lg">
                <Group justify="space-between" wrap="wrap">
                    <Stack gap={2}>
                        <Group gap="sm" align="center">
                            <Title order={2}>
                                Review – Haushalt {result.haushalt_year}
                            </Title>
                            <Anchor component={Link} to="/admin/haushalt-import/guide" size="sm" c="dimmed">
                                Anleitung →
                            </Anchor>
                        </Group>
                        <Text size="sm" c="dimmed">
                            {result.pdf_filename} · geparst am {new Date(result.parsed_at).toLocaleString("de-DE", { timeZone: "Europe/Berlin" })}
                            {result.username_snapshot ? ` von ${result.username_snapshot}` : ""}
                        </Text>
                    </Stack>

                    {isConfirmed ? (
                        <Badge color="green" size="lg" variant="light">
                            Importiert am {new Date(result.confirmed_at!).toLocaleString("de-DE", { timeZone: "Europe/Berlin" })}
                            {result.confirmed_by_snapshot ? ` von ${result.confirmed_by_snapshot}` : ""}
                        </Badge>
                    ) : (
                        <Group gap="xs">
                            <Button
                                variant="subtle"
                                color="red"
                                size="sm"
                                loading={deleteResult.isPending}
                                onClick={handleDiscard}
                            >
                                Verwerfen
                            </Button>
                            <Button
                                color="green"
                                size="sm"
                                loading={confirm.isPending}
                                onClick={handleConfirm}
                            >
                                Importieren
                            </Button>
                        </Group>
                    )}
                </Group>

                {result.status === "FAILURE" && (
                    <Alert color="red" variant="light" title="Parser-Fehler">
                        {result.error_message}
                    </Alert>
                )}

                <ReviewTable
                    rows={displayRows}
                    projects={projects ?? []}
                    onProjectIdsChange={handleProjectIdsChange}
                    readonly={isConfirmed}
                />
            </Stack>
        </Container>
    );
}
