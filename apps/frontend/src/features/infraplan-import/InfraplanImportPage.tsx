import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
    Anchor,
    Badge,
    Button,
    Container,
    FileInput,
    Group,
    NumberInput,
    Paper,
    Stack,
    Table,
    Tabs,
    Text,
    Title,
} from "@mantine/core";
import { openConfirmModal } from "../../shared/ui/confirmModal";
import { notifications } from "@mantine/notifications";
import RequirePermission from "../../components/RequirePermission";
import {
    useDeleteInfraplanParseResult,
    useDeleteInfraplanReport,
    useInfraplanParseResults,
    useInfraplanReports,
    useReparseInfraplan,
    useStartInfraplanImport,
    type InfraplanParseResultListItem,
    type InfraplanReport,
} from "../../shared/api/queries";
import { exceedsUploadLimit, tooLargeMessage, uploadErrorMessage } from "../../shared/api/uploads";
import { formatDateShort, formatDateTime } from "../../shared/format";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import { TaskProgressIndicator, useImportTask } from "../import-review/shared";
import InfraplanKpiSettings from "./InfraplanKpiSettings";
import { LoadingState } from "../../shared/ui/LoadingState";
import { STATUS_TONE } from "../../shared/theme/semanticColors";

const STATUS_LABEL: Record<string, { label: string; color: string }> = {
    PENDING: { label: "wartet", color: STATUS_TONE.neutral },
    RUNNING: { label: "wird gelesen", color: STATUS_TONE.active },
    SUCCESS: { label: "gelesen", color: STATUS_TONE.done },
    FAILURE: { label: "Fehler", color: STATUS_TONE.danger },
};

function errorDetail(error: unknown, fallback: string): string {
    return (error as { details?: { detail?: string } } | undefined)?.details?.detail ?? fallback;
}

function Drafts({ drafts }: { drafts: InfraplanParseResultListItem[] }) {
    const navigate = useNavigate();
    const deleteDraft = useDeleteInfraplanParseResult();
    const reparse = useReparseInfraplan();

    const handleDelete = (d: InfraplanParseResultListItem) =>
        openConfirmModal({
            title: "Entwurf verwerfen?",
            children: (
                <Text size="sm">
                    Der Entwurf „{d.file_name}“ ({d.year}) wird samt gespeichertem PDF gelöscht. Alle Zuordnungen
                    darin gehen verloren.
                </Text>
            ),
            labels: { confirm: "Verwerfen", cancel: "Abbrechen" },
            danger: true,
            onConfirm: async () => {
                try {
                    await deleteDraft.mutateAsync(d.id);
                } catch (error) {
                    notifications.show({ color: "red", message: errorDetail(error, "Löschen fehlgeschlagen.") });
                }
            },
        });

    const handleReparse = (d: InfraplanParseResultListItem) =>
        openConfirmModal({
            title: "Erneut auslesen?",
            children: (
                <Text size="sm">
                    Das gespeicherte PDF wird neu gelesen. Bestehende Zuordnungen bleiben je Zeile erhalten.
                </Text>
            ),
            labels: { confirm: "Neu auslesen", cancel: "Abbrechen" },
            onConfirm: async () => {
                try {
                    await reparse.mutateAsync(d.id);
                    notifications.show({ color: "blue", message: "Auslesen gestartet." });
                } catch (error) {
                    notifications.show({ color: "red", message: errorDetail(error, "Neu auslesen fehlgeschlagen.") });
                }
            },
        });

    if (drafts.length === 0) {
        return <Text c="dimmed" size="sm">Noch keine Entwürfe vorhanden.</Text>;
    }
    return (
        <ResponsiveTable minWidth={760} striped highlightOnHover withTableBorder>
            <Table.Thead>
                <Table.Tr>
                    <Table.Th>Jahrgang</Table.Th>
                    <Table.Th>Datei</Table.Th>
                    <Table.Th>Hochgeladen</Table.Th>
                    <Table.Th data-role="status">Status</Table.Th>
                    <Table.Th className="num">Zugeordnet / Zeilen</Table.Th>
                    <Table.Th className="num">Warnungen</Table.Th>
                    <Table.Th>Übernommen</Table.Th>
                    <Table.Th />
                </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
                {drafts.map((d) => {
                    const status = STATUS_LABEL[d.status] ?? { label: d.status, color: "gray" };
                    const warnings = d.warnings_json?.length ?? 0;
                    return (
                        <Table.Tr key={d.id}>
                            <Table.Td fw={600}>{d.year}</Table.Td>
                            <Table.Td style={{ maxWidth: 220, overflowWrap: "anywhere" }}>{d.file_name}</Table.Td>
                            <Table.Td>
                                <Text size="sm">{formatDateTime(d.created_at)}</Text>
                                {d.username_snapshot && <Text size="xs" c="dimmed">{d.username_snapshot}</Text>}
                            </Table.Td>
                            <Table.Td>
                                <Badge color={status.color} variant="light">{status.label}</Badge>
                                {d.error_message && (
                                    <Text size="xs" c="red" style={{ maxWidth: 220 }}>{d.error_message}</Text>
                                )}
                            </Table.Td>
                            <Table.Td className="num">{d.row_count == null ? "–" : `${d.assigned_count} / ${d.row_count}`}</Table.Td>
                            <Table.Td className="num">
                                {warnings > 0 ? <Badge color="gray" variant="outline">{warnings}</Badge> : "–"}
                            </Table.Td>
                            <Table.Td>
                                {d.confirmed_at ? (
                                    <Text size="sm">
                                        {formatDateTime(d.confirmed_at)}
                                        {d.confirmed_by_snapshot ? ` · ${d.confirmed_by_snapshot}` : ""}
                                    </Text>
                                ) : (
                                    "–"
                                )}
                            </Table.Td>
                            <Table.Td>
                                <Group gap="xs" justify="flex-end" wrap="nowrap">
                                    {d.status === "SUCCESS" && (
                                        <Button
                                            size="xs"
                                            variant="light"
                                            onClick={() => navigate(`/admin/infraplan-import/review/${d.id}`)}
                                        >
                                            {d.confirmed_at ? "Ansehen" : "Prüfen"}
                                        </Button>
                                    )}
                                    {!d.confirmed_at && (d.status === "SUCCESS" || d.status === "FAILURE") && (
                                        <Button size="xs" variant="subtle" onClick={() => handleReparse(d)}>
                                            Neu auslesen
                                        </Button>
                                    )}
                                    {!d.confirmed_at && (
                                        <Button size="xs" variant="subtle" color="red" onClick={() => handleDelete(d)}>
                                            Verwerfen
                                        </Button>
                                    )}
                                </Group>
                            </Table.Td>
                        </Table.Tr>
                    );
                })}
            </Table.Tbody>
        </ResponsiveTable>
    );
}

function Years({ reports }: { reports: InfraplanReport[] }) {
    const deleteReport = useDeleteInfraplanReport();

    const handleDelete = (r: InfraplanReport) =>
        openConfirmModal({
            title: `Infraplan ${r.year} löschen?`,
            children: (
                <Text size="sm">
                    Alle {r.entry_count} Einträge, ihre Projektzuordnungen und {r.kpi_value_count} Kennzahlwerte des
                    Jahrgangs werden gelöscht; der Planungsstand der betroffenen Projekte wird neu berechnet. Der
                    Entwurf bleibt erhalten und kann danach erneut übernommen werden.
                </Text>
            ),
            labels: { confirm: "Jahrgang löschen", cancel: "Abbrechen" },
            danger: true,
            onConfirm: async () => {
                try {
                    await deleteReport.mutateAsync(r.year);
                    notifications.show({ color: "green", message: `Infraplan ${r.year} gelöscht.` });
                } catch (error) {
                    notifications.show({ color: "red", message: errorDetail(error, "Löschen fehlgeschlagen.") });
                }
            },
        });

    if (reports.length === 0) {
        return <Text c="dimmed" size="sm">Noch kein Jahrgang übernommen.</Text>;
    }
    return (
        <ResponsiveTable minWidth={680} striped withTableBorder>
            <Table.Thead>
                <Table.Tr>
                    <Table.Th>Jahrgang</Table.Th>
                    <Table.Th>Veröffentlicht</Table.Th>
                    <Table.Th className="num">Einträge</Table.Th>
                    <Table.Th className="num">zugeordnet</Table.Th>
                    <Table.Th>Kennzahlen</Table.Th>
                    <Table.Th />
                </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
                {reports.map((r) => (
                    <Table.Tr key={r.id}>
                        <Table.Td>
                            <Text size="sm" fw={600}>{r.year}</Text>
                            {r.title && <Text size="xs" c="dimmed">{r.title}</Text>}
                        </Table.Td>
                        <Table.Td>{r.published_on ? formatDateShort(r.published_on) : "–"}</Table.Td>
                        <Table.Td className="num">{r.entry_count}</Table.Td>
                        <Table.Td className="num">{r.assigned_count}</Table.Td>
                        <Table.Td>
                            <Group gap={6} wrap="nowrap">
                                <Text size="sm">{r.kpi_value_count} Werte</Text>
                                {r.kpi_unchecked_count > 0 && (
                                    <Badge color="violet" variant="light" size="sm">
                                        {r.kpi_unchecked_count} ungeprüft
                                    </Badge>
                                )}
                            </Group>
                        </Table.Td>
                        <Table.Td>
                            <Group gap="xs" justify="flex-end" wrap="nowrap">
                                <Button size="xs" variant="light" component={Link} to={`/admin/infraplan/kpis/${r.year}`}>
                                    Kennzahlen
                                </Button>
                                {r.parse_result_id != null && (
                                    <Button
                                        size="xs"
                                        variant="subtle"
                                        component={Link}
                                        to={`/admin/infraplan-import/review/${r.parse_result_id}`}
                                    >
                                        Entwurf
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

function InfraplanImportPageContent() {
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();
    const tab = searchParams.get("tab") === "allgemeines" ? "allgemeines" : "import";
    const [file, setFile] = useState<File | null>(null);
    const [year, setYear] = useState<number | string>(new Date().getFullYear());
    const { data: drafts, isLoading: draftsLoading } = useInfraplanParseResults();
    const { data: reports, isLoading: reportsLoading } = useInfraplanReports();
    const startImport = useStartInfraplanImport();
    const [pendingId, setPendingId] = useState<number | null>(null);
    const task = useImportTask({
        onSuccess: () => {
            if (pendingId !== null) navigate(`/admin/infraplan-import/review/${pendingId}`);
        },
    });

    const yearNum = typeof year === "number" ? year : Number(year);
    const yearValid = Number.isInteger(yearNum) && yearNum >= 2020 && yearNum <= 2100;

    const handleUpload = async () => {
        if (!file || !yearValid) return;
        if (exceedsUploadLimit(file)) {
            notifications.show({ color: "red", title: "Datei zu groß", message: tooLargeMessage(file) });
            return;
        }
        try {
            const { task_id, parse_result_id } = await startImport.mutateAsync({ pdf: file, year: yearNum });
            setPendingId(parse_result_id);
            task.start(task_id);
        } catch (error) {
            notifications.show({ color: "red", message: uploadErrorMessage(error) });
        }
    };

    return (
        <Container size="lg" py="xl">
            <Stack gap="xl">
                <Stack gap={4}>
                    <Title order={1}>Infraplan</Title>
                    <Text size="sm" c="dimmed">
                        Infraplan des Bundes (Fünfjahresplan Schiene): Maßnahmentabellen einlesen, Projekten zuordnen,
                        Kennzahlen erfassen. Schritt für Schritt in der{" "}
                        <Anchor component={Link} to="/admin/anleitungen/infraplan" size="sm">Anleitung</Anchor>.
                    </Text>
                </Stack>
                <Tabs
                    value={tab}
                    onChange={(v) => setSearchParams(v === "import" ? {} : { tab: v ?? "import" }, { replace: true })}
                >
                    <Tabs.List>
                        <Tabs.Tab value="import">Import</Tabs.Tab>
                        <Tabs.Tab value="allgemeines">Allgemeines</Tabs.Tab>
                    </Tabs.List>
                    <Tabs.Panel value="allgemeines" pt="md">
                        <Paper withBorder p="var(--card-pad)">
                            <Stack gap="md">
                                <Text fw={600}>Kennzahlen</Text>
                                <InfraplanKpiSettings />
                            </Stack>
                        </Paper>
                    </Tabs.Panel>
                    <Tabs.Panel value="import" pt="md">
                        <Stack gap="xl">
                            <Paper withBorder p="var(--card-pad)">
                                <Stack gap="md">
                                    <Text fw={600}>Neuer Jahrgang</Text>
                                    <Text size="sm" c="dimmed">
                                        PDF des Infraplans hochladen. Das Auslesen startet automatisch; danach öffnet sich die
                                        Prüfansicht. Die Zuordnung kann auch ein KI-Agent über den MCP-Server übernehmen (Skill
                                        „infraplan-import“).
                                    </Text>
                                    <Group align="flex-end" gap="sm" wrap="wrap">
                                        <NumberInput
                                            label="Jahrgang"
                                            value={year}
                                            onChange={setYear}
                                            min={2020}
                                            max={2100}
                                            allowDecimal={false}
                                            w={120}
                                        />
                                        <FileInput
                                            label="PDF-Datei"
                                            placeholder="PDF auswählen..."
                                            accept="application/pdf"
                                            value={file}
                                            onChange={setFile}
                                            w={{ base: "100%", xs: 320 }}
                                        />
                                        <Button
                                            onClick={handleUpload}
                                            loading={startImport.isPending || task.isRunning}
                                            disabled={!file || !yearValid}
                                        >
                                            PDF lesen
                                        </Button>
                                    </Group>
                                    {task.isRunning && <TaskProgressIndicator progress={task.progress} warning={task.warning} />}
                                </Stack>
                            </Paper>
                            <Paper withBorder p="var(--card-pad)">
                                <Stack gap="md">
                                    <Text fw={600}>Entwürfe</Text>
                                    {draftsLoading ? <LoadingState rows={6} /> : <Drafts drafts={drafts ?? []} />}
                                </Stack>
                            </Paper>
                            <Paper withBorder p="var(--card-pad)">
                                <Stack gap="md">
                                    <Text fw={600}>Übernommene Jahrgänge</Text>
                                    {reportsLoading ? <LoadingState rows={6} /> : <Years reports={reports ?? []} />}
                                </Stack>
                            </Paper>
                        </Stack>
                    </Tabs.Panel>
                </Tabs>
            </Stack>
        </Container>
    );
}

export default function InfraplanImportPage() {
    return (
        <RequirePermission perm="infraplan.import">
            <InfraplanImportPageContent />
        </RequirePermission>
    );
}
