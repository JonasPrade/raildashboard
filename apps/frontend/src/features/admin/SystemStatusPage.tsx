/**
 * Systemstatus — „läuft im Hintergrund überhaupt jemand?"
 *
 * Imports (Haushalt, VIB, Fulda, Bauportal) run as Celery jobs. If no worker is
 * running, the upload still succeeds and the page waits forever: Celery reports
 * the same PENDING for „queued" and for „nobody is listening". This page makes
 * that difference visible — broker, workers, queue length — and names the
 * command that answers the next question.
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
    Table,
    Text,
} from "@mantine/core";
import { IconRefresh } from "@tabler/icons-react";

import { ChronicleCard, ChronicleHeadline } from "../../components/chronicle";
import RequirePermission from "../../components/RequirePermission";
import { useRecheckWorkerHealth, useWorkerHealth, type WorkerHealth } from "../../shared/api/queries";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";

const STATUS_DISPLAY: Record<WorkerHealth["status"], { color: string; label: string }> = {
    ok: { color: "green", label: "Worker laufen" },
    no_workers: { color: "red", label: "Kein Worker online" },
    broker_unreachable: { color: "red", label: "Warteschlange nicht erreichbar" },
};

function formatCheckedAt(checkedAt: number): string {
    return new Date(checkedAt * 1000).toLocaleTimeString("de-DE");
}

function WorkerTable({ health }: { health: WorkerHealth }) {
    if (health.workers.length === 0) return null;
    return (
        <ResponsiveTable minWidth={520} withTableBorder withColumnBorders>
            <Table.Thead>
                <Table.Tr>
                    <Table.Th>Worker</Table.Th>
                    <Table.Th>Parallelität</Table.Th>
                    <Table.Th>Aufträge in Arbeit</Table.Th>
                </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
                {health.workers.map((worker) => (
                    <Table.Tr key={worker.name}>
                        <Table.Td><Code>{worker.name}</Code></Table.Td>
                        <Table.Td>{worker.concurrency ?? "—"}</Table.Td>
                        <Table.Td>
                            {worker.active_tasks === 0
                                ? "bereit (nichts in Arbeit)"
                                : `${worker.active_tasks} — ${worker.active_task_names.join(", ")}`}
                        </Table.Td>
                    </Table.Tr>
                ))}
            </Table.Tbody>
        </ResponsiveTable>
    );
}

function SystemStatusPageContent() {
    const { data: health, isLoading, isError } = useWorkerHealth();
    const recheck = useRecheckWorkerHealth();

    return (
        <Container size="md" py="xl">
            <Stack gap="lg">
                <Group justify="space-between" align="center">
                    <ChronicleHeadline as="h1">Systemstatus</ChronicleHeadline>
                    <Button
                        variant="light"
                        leftSection={<IconRefresh size={16} />}
                        loading={recheck.isPending}
                        onClick={() => recheck.mutate()}
                    >
                        Erneut prüfen
                    </Button>
                </Group>

                <Text size="sm" c="dimmed">
                    Importe (Haushalt, VIB, Fulda, Bauportal) laufen als Hintergrund-Aufträge. Sie
                    werden von einem <b>Celery-Worker</b> abgearbeitet, der die Aufträge aus der
                    Warteschlange (Redis) zieht. Fehlt der Worker, nimmt die Anwendung den Auftrag
                    zwar an, aber niemand führt ihn aus — der Import bleibt dann endlos im Zustand
                    „wird verarbeitet".
                </Text>

                <ChronicleCard>
                    <Stack gap="md">
                        {isLoading && (
                            <Group gap="xs"><Loader size="xs" /><Text size="sm">Prüfung läuft…</Text></Group>
                        )}

                        {isError && (
                            <Alert color="red" variant="light" title="Prüfung nicht möglich">
                                Der Status konnte nicht abgefragt werden. Läuft das Backend, und ist
                                die Berechtigung „App-Einstellungen" gesetzt?
                            </Alert>
                        )}

                        {health && (
                            <>
                                <Group gap="sm" align="center">
                                    <Badge color={STATUS_DISPLAY[health.status].color} variant="filled">
                                        {STATUS_DISPLAY[health.status].label}
                                    </Badge>
                                    <Text size="sm" c="dimmed">
                                        geprüft um {formatCheckedAt(health.checked_at)}
                                    </Text>
                                </Group>

                                <Alert
                                    color={health.status === "ok" ? "green" : "orange"}
                                    variant="light"
                                >
                                    {health.message}
                                </Alert>

                                <WorkerTable health={health} />

                                <ResponsiveTable minWidth={480} variant="vertical" withTableBorder>
                                    <Table.Tbody>
                                        <Table.Tr>
                                            <Table.Th w={220}>Warteschlange (Broker)</Table.Th>
                                            <Table.Td>
                                                <Code>{health.broker_url || "—"}</Code>{" "}
                                                {health.broker_reachable ? "erreichbar" : "nicht erreichbar"}
                                            </Table.Td>
                                        </Table.Tr>
                                        <Table.Tr>
                                            <Table.Th>Wartende Aufträge</Table.Th>
                                            <Table.Td>
                                                {health.queued_tasks ?? "unbekannt (kein Redis-Broker)"}
                                            </Table.Td>
                                        </Table.Tr>
                                        {health.detail && (
                                            <Table.Tr>
                                                <Table.Th>Technische Meldung</Table.Th>
                                                <Table.Td><Code>{health.detail}</Code></Table.Td>
                                            </Table.Tr>
                                        )}
                                    </Table.Tbody>
                                </ResponsiveTable>
                            </>
                        )}
                    </Stack>
                </ChronicleCard>

                <ChronicleCard>
                    <Stack gap="xs">
                        <Text fw={600} size="md">Wenn kein Worker läuft</Text>
                        <Text size="sm">
                            Auf dem Server (Verzeichnis des Stacks):
                        </Text>
                        <Code block>{"docker compose ps worker\ndocker compose logs --tail=50 worker\ndocker compose up -d worker"}</Code>
                        <Text size="sm">
                            Lokal in der Entwicklung startet <Code>make celery-worker</Code> den
                            Worker (Redis muss laufen: <Code>make docker-dev-up</Code>).
                        </Text>
                        <Text size="sm" c="dimmed">
                            Ein Import, der während eines Worker-Neustarts hochgeladen wurde, ist
                            verloren — die Datei danach einfach erneut hochladen.
                        </Text>
                    </Stack>
                </ChronicleCard>
            </Stack>
        </Container>
    );
}

export default function SystemStatusPage() {
    return (
        <RequirePermission perm="settings.manage">
            <SystemStatusPageContent />
        </RequirePermission>
    );
}
