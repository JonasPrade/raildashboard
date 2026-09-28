/**
 * Abgeordnetenstand — the admin entry point for the constituency/MP feature.
 *
 * Two Celery jobs with very different cost (see tasks/parliament.py): the
 * people refresh is cheap and meant to be rerun whenever substitutes or
 * committee reshuffles happen; the link rebuild is the full ST_Intersection
 * over the portfolio and only needed after a geometry import or a new
 * legislative period. The geometries themselves come from a CLI script, so this
 * page only reports whether they are there.
 */

import {
    Alert,
    Badge,
    Button,
    Code,
    Container,
    Group,
    Loader,
    Stack,
    Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconRefresh, IconRoute } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";

import { ChronicleCard, ChronicleHeadline } from "../../components/chronicle";
import RequirePermission from "../../components/RequirePermission";
import {
    type ParliamentStatus,
    queryKeys,
    useParliamentStatus,
    useStartConstituencyLinkRebuild,
    useStartParliamentImport,
} from "../../shared/api/queries";
import { useImportTask } from "../import-review/shared";

type ImportRun = NonNullable<ParliamentStatus["last_politician_import"]>;

function formatDateTime(value: string | null | undefined): string {
    if (!value) return "—";
    return new Date(value).toLocaleString("de-DE", {
        timeZone: "Europe/Berlin",
        dateStyle: "medium",
        timeStyle: "short",
    });
}

function RunLine({ label, run }: { label: string; run: ImportRun | null | undefined }) {
    return (
        <Group gap="xs" wrap="wrap">
            <Text size="sm" fw={500}>{label}:</Text>
            {run ? (
                <>
                    <Text size="sm">{formatDateTime(run.finished_at ?? run.started_at)}</Text>
                    <Badge
                        size="xs"
                        variant="light"
                        color={run.status === "success" ? "green" : run.status === "error" ? "red" : "gray"}
                    >
                        {run.status === "success" ? "erfolgreich" : run.status === "error" ? "Fehler" : "läuft"}
                    </Badge>
                </>
            ) : (
                <Text size="sm" c="dimmed">noch nie</Text>
            )}
        </Group>
    );
}

/** Launch button + progress for one parliament job. */
function useParliamentJob(successTitle: string, failureTitle: string) {
    const queryClient = useQueryClient();
    const task = useImportTask({
        onSuccess: () => {
            task.reset();
            // Everything on the MP pages derives from these runs.
            queryClient.invalidateQueries({ queryKey: queryKeys.parliamentStatus });
            queryClient.invalidateQueries({ queryKey: queryKeys.politicians });
            queryClient.invalidateQueries({ queryKey: queryKeys.constituencies });
            notifications.show({ color: "green", title: successTitle, message: "Der neue Stand ist sichtbar." });
        },
        onFailure: (error) => {
            queryClient.invalidateQueries({ queryKey: queryKeys.parliamentStatus });
            notifications.show({
                color: "red",
                title: failureTitle,
                message: error ?? "Unbekannter Fehler — Details im Worker-Log.",
                autoClose: false,
            });
        },
    });
    return task;
}

function ParliamentAdminPageContent() {
    const { data: status, isLoading } = useParliamentStatus();
    const startImport = useStartParliamentImport();
    const startLinks = useStartConstituencyLinkRebuild();
    const importTask = useParliamentJob("Abgeordnetenstand aktualisiert", "Abgeordneten-Import fehlgeschlagen");
    const linkTask = useParliamentJob("Wahlkreis-Zuordnung neu berechnet", "Neuberechnung fehlgeschlagen");

    const launch = (
        mutation: typeof startImport,
        task: typeof importTask,
        failureTitle: string,
    ) =>
        mutation.mutate(undefined, {
            onSuccess: (response) => task.start(response.task_id),
            onError: (error) =>
                notifications.show({
                    color: "red",
                    title: failureTitle,
                    message: error instanceof Error ? error.message : "Auftrag konnte nicht gestartet werden.",
                }),
        });

    const importBusy = startImport.isPending || importTask.taskId !== null;
    const linksBusy = startLinks.isPending || linkTask.taskId !== null;

    const counts = status?.counts ?? {};
    const coverage = status?.coverage ?? {};
    const withGeometry = counts.constituencies_with_geometry ?? 0;

    return (
        <Container size="md" py="xl">
            <Stack gap="lg">
                <Stack gap={4}>
                    <ChronicleHeadline as="h1">Abgeordnetenstand</ChronicleHeadline>
                    <Text c="dimmed" size="sm">
                        Abgeordnete, Mandate und Ausschussmitgliedschaften kommen von
                        abgeordnetenwatch.de (API v2, CC0). Die Wahlkreisgeometrien kommen einmal je
                        Wahl per Skript; daraus wird die Zuordnung Projekt ↔ Wahlkreis berechnet.
                    </Text>
                </Stack>

                {isLoading ? (
                    <Group justify="center" py="md"><Loader /></Group>
                ) : status ? (
                    <ChronicleCard>
                        <Stack gap="xs">
                            <Group gap="xs">
                                <Text size="sm" fw={500}>Wahlperiode:</Text>
                                <Text size="sm">{status.period?.label ?? "noch keine importiert"}</Text>
                                {status.is_stale && status.period && (
                                    <Badge size="xs" color="gold" variant="light">
                                        älter als {status.stale_after_days} Tage
                                    </Badge>
                                )}
                            </Group>
                            <RunLine label="Abgeordnete" run={status.last_politician_import} />
                            <RunLine label="Wahlkreisgeometrien" run={status.last_constituency_import} />
                            <RunLine label="Projekt-Zuordnung" run={status.last_link_run} />
                            <Text size="sm" c="dimmed">
                                {counts.mandates ?? 0} Mandate · {counts.direct_mandates ?? 0} Direktmandate ·{" "}
                                {withGeometry} von {counts.constituencies ?? 0} Wahlkreisen mit Geometrie ·{" "}
                                {coverage.projects_linked ?? 0} von {coverage.projects_with_geometry ?? 0} Projekten
                                mit Geometrie zugeordnet
                            </Text>
                            {status.last_link_run?.status === "error" && status.last_link_run.error && (
                                <Text size="xs" c="red">Letzter Fehler: {status.last_link_run.error}</Text>
                            )}
                            {status.last_politician_import?.status === "error" &&
                                status.last_politician_import.error && (
                                    <Text size="xs" c="red">
                                        Letzter Fehler: {status.last_politician_import.error}
                                    </Text>
                                )}
                        </Stack>
                    </ChronicleCard>
                ) : null}

                <ChronicleCard>
                    <Stack gap="sm">
                        <Text fw={500}>Abgeordnetenstand aktualisieren</Text>
                        <Text size="sm" c="dimmed">
                            Lädt Wahlperiode, Wahlkreise, Mandate und die Mitglieder von Verkehrs- und
                            Haushaltsausschuss neu. Idempotent — nach Nachrückern oder Ausschussumbesetzungen einfach erneut ausführen.
                        </Text>
                        <Group>
                            <Button
                                leftSection={<IconRefresh size={16} />}
                                loading={importBusy}
                                onClick={() => launch(startImport, importTask, "Import konnte nicht gestartet werden")}
                            >
                                Abgeordnetenstand aktualisieren
                            </Button>
                        </Group>
                        {importTask.warning && (
                            <Alert color="orange" variant="light">{importTask.warning}</Alert>
                        )}
                    </Stack>
                </ChronicleCard>

                <ChronicleCard>
                    <Stack gap="sm">
                        <Text fw={500}>Projekt-Wahlkreis-Zuordnung neu berechnen</Text>
                        <Text size="sm" c="dimmed">
                            Verschneidet alle Projektgeometrien mit den Wahlkreisen. Nur nach einem
                            Geometrie-Import oder einer neuen Wahlperiode nötig — Änderungen an einzelnen
                            Projektgeometrien werden automatisch nachgezogen.
                        </Text>
                        {status && withGeometry === 0 && (
                            <Alert color="gray" variant="light">
                                Es sind noch keine Wahlkreisgeometrien vorhanden. Sie werden auf dem Server
                                per Skript importiert (<Code>scripts/import_constituencies.py</Code>, siehe
                                Backend-README); ohne sie bleibt die Zuordnung leer.
                            </Alert>
                        )}
                        <Group>
                            <Button
                                variant="light"
                                leftSection={<IconRoute size={16} />}
                                loading={linksBusy}
                                disabled={status != null && withGeometry === 0}
                                onClick={() => launch(startLinks, linkTask, "Neuberechnung konnte nicht gestartet werden")}
                            >
                                Zuordnung neu berechnen
                            </Button>
                        </Group>
                        {linkTask.warning && (
                            <Alert color="orange" variant="light">{linkTask.warning}</Alert>
                        )}
                    </Stack>
                </ChronicleCard>
            </Stack>
        </Container>
    );
}

export default function ParliamentAdminPage() {
    return (
        <RequirePermission
            perm="parliament.import"
            message="Für diese Seite ist das Recht „Abgeordnetenstand aktualisieren“ (parliament.import) nötig."
        >
            <ParliamentAdminPageContent />
        </RequirePermission>
    );
}
