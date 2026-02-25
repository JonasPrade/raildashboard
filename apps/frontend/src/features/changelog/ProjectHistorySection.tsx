import { useState } from "react";
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
    Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import {
    useProjectChangelog,
    useRevertProjectField,
    type ChangeLog,
    type ChangeLogEntry,
} from "../../shared/api/queries";

// German labels for all tracked project fields
const FIELD_LABELS: Record<string, string> = {
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

function fieldLabel(fieldName: string): string {
    return FIELD_LABELS[fieldName] ?? fieldName;
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
        default:
            return action;
    }
}

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
        <Accordion.Item value={String(log.id)}>
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
                                <Table.Td fw={500}>{fieldLabel(entry.field_name)}</Table.Td>
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

type ProjectHistorySectionProps = {
    projectId: number;
    canEdit: boolean;
};

export default function ProjectHistorySection({ projectId, canEdit }: ProjectHistorySectionProps) {
    const { data, isLoading, isError } = useProjectChangelog(projectId);
    const revertMutation = useRevertProjectField(projectId);
    const [revertingEntryId, setRevertingEntryId] = useState<number | null>(null);

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

    if (!data || data.length === 0) {
        return (
            <Text size="sm" c="dimmed">
                Noch keine Änderungen aufgezeichnet.
            </Text>
        );
    }

    return (
        <Stack gap="xs">
            <Title order={4}>Versionshistorie</Title>
            <Accordion variant="separated" chevronPosition="right">
                {data.map((log) => (
                    <ChangeLogItem
                        key={log.id}
                        log={log}
                        canEdit={canEdit}
                        revertingEntryId={revertingEntryId}
                        onRevert={handleRevert}
                    />
                ))}
            </Accordion>
        </Stack>
    );
}
