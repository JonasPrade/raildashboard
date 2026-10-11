import { useMemo, useState } from "react";
import {
    Accordion,
    Alert,
    Button,
    Group,
    Loader,
    Stack,
    Table,
    Text,
} from "@mantine/core";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import { ChronicleDataChip } from "../../components/chronicle";
import { notifications } from "@mantine/notifications";

import {
    useProjectChangelog,
    useProjectGroups,
    useProjectTextChangelog,
    useRevertProjectField,
    type ChangeLog,
    type ChangeLogEntry,
    type TextChangeLog,
    type TextChangeLogEntry,
} from "../../shared/api/queries";
import { formatDateTimeShort } from "../../shared/format";

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
    geojson_from_subprojects: "Geometrie aus Unterprojekten",
    project_group_ids: "Projektgruppen",
};

// Planning-state changes share the project changelog under a "progress." prefix.
// They are history only: the revert endpoint accepts project fields alone.
const PROGRESS_PREFIX = "progress.";

const PROGRESS_FIELD_LABELS: Record<string, string> = {
    observation: "Beobachtung",
    has_planfeststellung: "Planfeststellung relevant",
    parl_befassung_relevant: "Parl. Befassung relevant",
    lifecycle_status: "Status",
    manual_phase_override: "Phase (manuell)",
    manual_override_note: "Begründung Override",
    pf_state_override: "Planfeststellung (manuell)",
    parl_state_override: "Parl. Befassung (manuell)",
    parl_befassung_text: "Parl. Befassung – Text",
    parl_drucksache_url: "Parl. Befassung – Drucksache",
    parl_befassung_date: "Parl. Befassung – Datum",
    pf_text: "Planfeststellung – Text",
    pf_date: "Planfeststellung – Datum",
    pf_links: "Planfeststellung – Links",
    pf_document: "Planfeststellung – Dokument",
    parl_document: "Parl. Befassung – Dokument",
};

function isProgressField(fieldName: string): boolean {
    return fieldName.startsWith(PROGRESS_PREFIX);
}

const TEXT_FIELD_LABELS: Record<string, string> = {
    header: "Überschrift",
    text: "Textinhalt",
    weblink: "Weblink",
    logo_url: "Logo-URL",
    type: "Typ",
};

function fieldLabel(fieldName: string, source: "project" | "text"): string {
    if (source === "project" && isProgressField(fieldName)) {
        const key = fieldName.slice(PROGRESS_PREFIX.length);
        return `Planungsstand: ${PROGRESS_FIELD_LABELS[key] ?? key}`;
    }
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
        if (typeof parsed === "object") return JSON.stringify(parsed);
        return String(parsed);
    } catch {
        return value;
    }
}


// Group memberships are logged as id lists (so they stay revertible); show short names.
function formatGroupIds(value: string | null | undefined, groupNames: Map<number, string>): string {
    if (value == null) return "–";
    try {
        const ids = JSON.parse(value);
        if (!Array.isArray(ids)) return formatValue(value);
        if (ids.length === 0) return "–";
        return ids.map((id: number) => groupNames.get(id) ?? `#${id}`).join(", ");
    } catch {
        return value;
    }
}

function formatEntryValue(
    entry: ChangeLogEntry,
    value: string | null | undefined,
    groupNames: Map<number, string>,
): string {
    return entry.field_name === "project_group_ids"
        ? formatGroupIds(value, groupNames)
        : formatValue(value);
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
    groupNames: Map<number, string>;
};

function ChangeLogItem({ log, canEdit, revertingEntryId, onRevert, groupNames }: ChangeLogItemProps) {
    const date = formatDateTimeShort(log.timestamp);
    const isProgressLog = log.entries.length > 0 && log.entries.every((e) => isProgressField(e.field_name));

    const summary = (
        <Group gap="sm" wrap="nowrap">
            <Text size="sm" fw={500} style={{ minWidth: 130 }}>
                {date}
            </Text>
            <ChronicleDataChip>{isProgressLog ? "Planungsstand" : "Projekt"}</ChronicleDataChip>
            <ChronicleDataChip>{actionLabel(log.action)}</ChronicleDataChip>
            <Text size="sm" c="dimmed">
                {log.username_snapshot ?? "–"}
            </Text>
            <ChronicleDataChip>
                {log.entries.length} {log.entries.length === 1 ? "Feld" : "Felder"}
            </ChronicleDataChip>
        </Group>
    );

    return (
        <Accordion.Item value={`project-${log.id}`}>
            <Accordion.Control>{summary}</Accordion.Control>
            <Accordion.Panel>
                <ResponsiveTable minWidth={640} striped withTableBorder fz="sm">
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
                                <Table.Td c="dimmed">
                                    {formatEntryValue(entry, entry.old_value, groupNames)}
                                </Table.Td>
                                <Table.Td>{formatEntryValue(entry, entry.new_value, groupNames)}</Table.Td>
                                {canEdit && isProgressField(entry.field_name) && <Table.Td />}
                                {canEdit && !isProgressField(entry.field_name) && (
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
                </ResponsiveTable>
            </Accordion.Panel>
        </Accordion.Item>
    );
}

// ── Text changelog item ───────────────────────────────────────────────────────

type TextChangeLogItemProps = {
    log: TextChangeLog;
};

function TextChangeLogItem({ log }: TextChangeLogItemProps) {
    const date = formatDateTimeShort(log.timestamp);

    const summary = (
        <Group gap="sm" wrap="nowrap">
            <Text size="sm" fw={500} style={{ minWidth: 130 }}>
                {date}
            </Text>
            <ChronicleDataChip>Text</ChronicleDataChip>
            <ChronicleDataChip>{actionLabel(log.action)}</ChronicleDataChip>
            <Text size="sm" c="dimmed">
                {log.username_snapshot ?? "–"}
            </Text>
            {log.text_header_snapshot && (
                <Text size="sm" c="dimmed" fs="italic">
                    „{log.text_header_snapshot}"
                </Text>
            )}
            {log.entries.length > 0 && (
                <ChronicleDataChip>
                    {log.entries.length} {log.entries.length === 1 ? "Feld" : "Felder"}
                </ChronicleDataChip>
            )}
        </Group>
    );

    return (
        <Accordion.Item value={`text-${log.id}`}>
            <Accordion.Control>{summary}</Accordion.Control>
            <Accordion.Panel>
                {log.entries.length > 0 ? (
                    <ResponsiveTable minWidth={640} striped withTableBorder fz="sm">
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
                    </ResponsiveTable>
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
    const { data: projectGroups } = useProjectGroups();
    const groupNames = useMemo(
        () =>
            new Map<number, string>(
                (projectGroups ?? [])
                    .filter((g) => g.id != null)
                    .map((g) => [g.id as number, g.short_name ?? g.name ?? `#${g.id}`]),
            ),
        [projectGroups],
    );
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
                            groupNames={groupNames}
                        />
                    ) : (
                        <TextChangeLogItem key={`text-${entry.log.id}`} log={entry.log} />
                    ),
                )}
            </Accordion>
        </Stack>
    );
}
