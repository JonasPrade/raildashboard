import { useMemo, useState } from "react";
import {
    Accordion,
    Alert,
    Badge,
    Button,
    Group,
    Loader,
    Stack,
    Table,
    Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import {
    useProjectChangelog,
    useProjectTextChangelog,
    useRevertProjectField,
    type ChangeLog,
    type ChangeLogEntry,
    type TextChangeLog,
    type TextChangeLogEntry,
} from "../../shared/api/queries";

// German labels for all tracked project fields
const PROJECT_FIELD_LABELS: Record<string, string> = {
    name: "Name",
    project_number: "Projektnummer",
    description: "Beschreibung",
    justification: "Begründung",
    length: "Länge (km)",
    superior_project_id: "Übergeordnetes Projekt",
    effects_passenger_long_rail: "Fernverkehr",
    effects_passenger_local_rail: "Nahverkehr",
    effects_cargo_rail: "Güterverkehr",
    nbs: "Neubaustrecke",
    abs: "Ausbaustrecke",
    elektrification: "Elektrifizierung",
    charging_station: "Ladestation",
    small_charging_station: "Kleine Ladestation",
    second_track: "Zweigleisigkeit",
    third_track: "Dreigleisigkeit",
    fourth_track: "Viergleisigkeit",
    curve: "Neue Verbindungskurve",
    platform: "Neuer Bahnsteig",
    junction_station: "Knotenbahnhof",
    number_junction_station: "Anzahl Knotenbahnhöfe",
    overtaking_station: "Überholbahnhof",
    number_overtaking_station: "Anzahl Überholbahnhöfe",
    double_occupancy: "Doppelbelegung",
    block_increase: "Blockerhöhung",
    flying_junction: "Überflieger",
    tunnel_structural_gauge: "Tunnellichtmaß",
    increase_speed: "Geschwindigkeitserhöhung",
    new_vmax: "Neue Vmax (km/h)",
    level_free_platform_entrance: "Niveaufreier Bahnsteigzugang",
    etcs: "ETCS",
    etcs_level: "ETCS-Level",
    station_railroad_switches: "Bahnhofsweichen",
    new_station: "Neuer Bahnhof",
    depot: "Depot",
    battery: "Batterie",
    h2: "Wasserstoff",
    efuel: "E-Fuel",
    closure: "Streckenstilllegung",
    optimised_electrification: "Optimierte Elektrifizierung",
    filling_stations_efuel: "Tankstellen E-Fuel",
    filling_stations_h2: "Tankstellen Wasserstoff",
    filling_stations_diesel: "Tankstellen Diesel",
    filling_stations_count: "Anzahl Tankstellen",
    sanierung: "Sanierung",
    sgv740m: "SGV 740m",
    railroad_crossing: "Bahnübergänge",
    new_estw: "Neues ESTW",
    new_dstw: "Neues DSTW",
    noise_barrier: "Lärmschutz",
    overpass: "Überleitstellen",
    buffer_track: "Puffergleis",
    gwb: "Gleiswechselbetrieb",
    simultaneous_train_entries: "Gleichzeitige Zugeinfahrten",
    tilting: "Neigetechnik",
    geojson_representation: "GeoJSON-Geometrie",
};

const TEXT_FIELD_LABELS: Record<string, string> = {
    header: "Überschrift",
    text: "Textinhalt",
    weblink: "Weblink",
    logo_url: "Logo-URL",
    type: "Typ",
};

function fieldLabel(fieldName: string, source: "project" | "text"): string {
    const labels = source === "project" ? PROJECT_FIELD_LABELS : TEXT_FIELD_LABELS;
    return labels[fieldName] ?? fieldName;
}

function formatValue(value: string | null | undefined): string {
    if (value == null) return "–";
    try {
        const parsed = JSON.parse(value);
        if (parsed === null) return "–";
        if (typeof parsed === "boolean") return parsed ? "Ja" : "Nein";
        if (typeof parsed === "string") return parsed || "–";
        return String(parsed);
    } catch {
        return value;
    }
}

function actionBadgeColor(action: string): string {
    switch (action) {
        case "REVERT":
            return "orange";
        case "PATCH":
            return "blue";
        case "CREATE":
            return "green";
        case "DELETE":
            return "red";
        default:
            return "gray";
    }
}

function actionLabel(action: string): string {
    switch (action) {
        case "REVERT":
            return "Rückgesetzt";
        case "PATCH":
            return "Geändert";
        case "CREATE":
            return "Erstellt";
        case "DELETE":
            return "Gelöscht";
        default:
            return action;
    }
}

// ── Project field changelog item ──────────────────────────────────────────────

type ChangeLogItemProps = {
    log: ChangeLog;
    canEdit: boolean;
    revertingEntryId: number | null;
    onRevert: (entryId: number) => void;
};

function ChangeLogItem({ log, canEdit, revertingEntryId, onRevert }: ChangeLogItemProps) {
    const date = new Date(log.timestamp).toLocaleString("de-DE", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });

    const summary = (
        <Group gap="sm" wrap="nowrap">
            <Text size="sm" fw={500} style={{ minWidth: 130 }}>
                {date}
            </Text>
            <Badge size="xs" variant="outline" color="petrol">
                Projekt
            </Badge>
            <Badge size="sm" color={actionBadgeColor(log.action)} variant="light">
                {actionLabel(log.action)}
            </Badge>
            <Text size="sm" c="dimmed">
                {log.username_snapshot ?? "–"}
            </Text>
            <Badge size="xs" variant="outline" color="gray">
                {log.entries.length} {log.entries.length === 1 ? "Feld" : "Felder"}
            </Badge>
        </Group>
    );

    return (
        <Accordion.Item value={`project-${log.id}`}>
            <Accordion.Control>{summary}</Accordion.Control>
            <Accordion.Panel>
                <Table striped withTableBorder fz="sm">
                    <Table.Thead>
                        <Table.Tr>
                            <Table.Th>Feld</Table.Th>
                            <Table.Th>Vorher</Table.Th>
                            <Table.Th>Nachher</Table.Th>
                            {canEdit && <Table.Th style={{ width: 120 }} />}
                        </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                        {log.entries.map((entry: ChangeLogEntry) => (
                            <Table.Tr key={entry.id}>
                                <Table.Td fw={500}>{fieldLabel(entry.field_name, "project")}</Table.Td>
                                <Table.Td c="dimmed">{formatValue(entry.old_value)}</Table.Td>
                                <Table.Td>{formatValue(entry.new_value)}</Table.Td>
                                {canEdit && (
                                    <Table.Td>
                                        <Button
                                            size="xs"
                                            variant="subtle"
                                            color="orange"
                                            loading={revertingEntryId === entry.id}
                                            disabled={
                                                revertingEntryId !== null &&
                                                revertingEntryId !== entry.id
                                            }
                                            onClick={() => onRevert(entry.id)}
                                        >
                                            Zurücksetzen
                                        </Button>
                                    </Table.Td>
                                )}
                            </Table.Tr>
                        ))}
                    </Table.Tbody>
                </Table>
            </Accordion.Panel>
        </Accordion.Item>
    );
}

// ── Text changelog item ───────────────────────────────────────────────────────

type TextChangeLogItemProps = {
    log: TextChangeLog;
};

function TextChangeLogItem({ log }: TextChangeLogItemProps) {
    const date = new Date(log.timestamp).toLocaleString("de-DE", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });

    const summary = (
        <Group gap="sm" wrap="nowrap">
            <Text size="sm" fw={500} style={{ minWidth: 130 }}>
                {date}
            </Text>
            <Badge size="xs" variant="outline" color="violet">
                Text
            </Badge>
            <Badge size="sm" color={actionBadgeColor(log.action)} variant="light">
                {actionLabel(log.action)}
            </Badge>
            <Text size="sm" c="dimmed">
                {log.username_snapshot ?? "–"}
            </Text>
            {log.text_header_snapshot && (
                <Text size="sm" c="dimmed" fs="italic">
                    „{log.text_header_snapshot}"
                </Text>
            )}
            {log.entries.length > 0 && (
                <Badge size="xs" variant="outline" color="gray">
                    {log.entries.length} {log.entries.length === 1 ? "Feld" : "Felder"}
                </Badge>
            )}
        </Group>
    );

    return (
        <Accordion.Item value={`text-${log.id}`}>
            <Accordion.Control>{summary}</Accordion.Control>
            <Accordion.Panel>
                {log.entries.length > 0 ? (
                    <Table striped withTableBorder fz="sm">
                        <Table.Thead>
                            <Table.Tr>
                                <Table.Th>Feld</Table.Th>
                                <Table.Th>Vorher</Table.Th>
                                <Table.Th>Nachher</Table.Th>
                            </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                            {log.entries.map((entry: TextChangeLogEntry) => (
                                <Table.Tr key={entry.id}>
                                    <Table.Td fw={500}>{fieldLabel(entry.field_name, "text")}</Table.Td>
                                    <Table.Td c="dimmed">{formatValue(entry.old_value)}</Table.Td>
                                    <Table.Td>{formatValue(entry.new_value)}</Table.Td>
                                </Table.Tr>
                            ))}
                        </Table.Tbody>
                    </Table>
                ) : (
                    <Text size="sm" c="dimmed">
                        Keine Felddetails verfügbar.
                    </Text>
                )}
            </Accordion.Panel>
        </Accordion.Item>
    );
}

// ── Unified timeline entry ────────────────────────────────────────────────────

type TimelineEntry =
    | { kind: "project"; log: ChangeLog; timestamp: number }
    | { kind: "text"; log: TextChangeLog; timestamp: number };

// ── Section ───────────────────────────────────────────────────────────────────

type ProjectHistorySectionProps = {
    projectId: number;
    canEdit: boolean;
};

export default function ProjectHistorySection({ projectId, canEdit }: ProjectHistorySectionProps) {
    const { data: projectLogs, isLoading: projectLoading, isError: projectError } = useProjectChangelog(projectId);
    const { data: textLogs, isLoading: textLoading, isError: textError } = useProjectTextChangelog(projectId);
    const revertMutation = useRevertProjectField(projectId);
    const [revertingEntryId, setRevertingEntryId] = useState<number | null>(null);

    const isLoading = projectLoading || textLoading;
    const isError = projectError || textError;

    // Merge and sort all entries by timestamp descending
    const timeline = useMemo<TimelineEntry[]>(() => {
        const entries: TimelineEntry[] = [];
        for (const log of projectLogs ?? []) {
            entries.push({ kind: "project", log, timestamp: new Date(log.timestamp).getTime() });
        }
        for (const log of textLogs ?? []) {
            entries.push({ kind: "text", log, timestamp: new Date(log.timestamp).getTime() });
        }
        return entries.sort((a, b) => b.timestamp - a.timestamp);
    }, [projectLogs, textLogs]);

    function handleRevert(entryId: number) {
        setRevertingEntryId(entryId);
        revertMutation.mutate(entryId, {
            onSuccess: () => {
                setRevertingEntryId(null);
                notifications.show({
                    color: "green",
                    title: "Feld zurückgesetzt",
                    message: "Der frühere Wert wurde wiederhergestellt.",
                });
            },
            onError: () => {
                setRevertingEntryId(null);
                notifications.show({
                    color: "red",
                    title: "Zurücksetzen fehlgeschlagen",
                    message: "Der Wert konnte nicht wiederhergestellt werden.",
                });
            },
        });
    }

    if (isLoading) {
        return <Loader size="sm" />;
    }

    if (isError) {
        return (
            <Alert color="red" variant="light">
                Versionshistorie konnte nicht geladen werden.
            </Alert>
        );
    }

    if (timeline.length === 0) {
        return (
            <Text size="sm" c="dimmed">
                Noch keine Änderungen aufgezeichnet.
            </Text>
        );
    }

    return (
        <Stack gap="xs">
            <Accordion variant="separated" chevronPosition="right">
                {timeline.map((entry) =>
                    entry.kind === "project" ? (
                        <ChangeLogItem
                            key={`project-${entry.log.id}`}
                            log={entry.log}
                            canEdit={canEdit}
                            revertingEntryId={revertingEntryId}
                            onRevert={handleRevert}
                        />
                    ) : (
                        <TextChangeLogItem key={`text-${entry.log.id}`} log={entry.log} />
                    ),
                )}
            </Accordion>
        </Stack>
    );
}
