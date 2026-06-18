import {
    Button,
    Divider,
    MultiSelect,
    NumberInput,
    Stack,
    Switch,
    Text,
    Textarea,
    TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Fragment, useMemo, useState } from "react";

import { useProjectGroups } from "../../shared/api/queries";
import { computeGeojsonLengthKm } from "../../shared/geo/length";
import type { ProjectEditFormValues } from "./ProjectEdit";

export type ProjectEditFieldsProps = {
    values: ProjectEditFormValues;
    setValues: React.Dispatch<React.SetStateAction<ProjectEditFormValues>>;
    /** Project geometry (geojson_representation). Enables "Länge aus Geometrie berechnen". */
    geojson?: string | null;
};

type BoolKey = {
    [K in keyof ProjectEditFormValues]: ProjectEditFormValues[K] extends boolean ? K : never;
}[keyof ProjectEditFormValues];

type NumKey = {
    [K in keyof ProjectEditFormValues]: ProjectEditFormValues[K] extends number | null ? K : never;
}[keyof ProjectEditFormValues];

type PropField =
    | { kind: "switch"; label: string; key: BoolKey }
    | { kind: "number"; label: string; key: NumKey; indent?: boolean };

/** The toggle/number property sections, data-driven so they can be filtered by search. */
const PROPERTY_SECTIONS: Array<{ label: string; fields: PropField[] }> = [
    {
        label: "Verkehrsarten",
        fields: [
            { kind: "switch", label: "Fernverkehr", key: "effects_passenger_long_rail" },
            { kind: "switch", label: "Nahverkehr", key: "effects_passenger_local_rail" },
            { kind: "switch", label: "Güterverkehr", key: "effects_cargo_rail" },
        ],
    },
    {
        label: "Streckenausbau",
        fields: [
            { kind: "switch", label: "Neubaustrecke (NBS)", key: "nbs" },
            { kind: "switch", label: "Ausbaustrecke (ABS)", key: "abs" },
            { kind: "switch", label: "Zweigleisiger Ausbau", key: "second_track" },
            { kind: "switch", label: "Dreigleisiger Ausbau", key: "third_track" },
            { kind: "switch", label: "Viergleisiger Ausbau", key: "fourth_track" },
            { kind: "switch", label: "Kurvenanhebung", key: "curve" },
            { kind: "switch", label: "Geschwindigkeitsanhebung", key: "increase_speed" },
            { kind: "number", label: "Neue Vmax (km/h)", key: "new_vmax", indent: true },
            { kind: "switch", label: "Tunnel Lichtraumprofil", key: "tunnel_structural_gauge" },
            { kind: "switch", label: "Neigetechnik", key: "tilting" },
        ],
    },
    {
        label: "Bahnhöfe & Infrastruktur",
        fields: [
            { kind: "switch", label: "Neuer Bahnhof", key: "new_station" },
            { kind: "switch", label: "Bahnsteig", key: "platform" },
            { kind: "switch", label: "Knotenbahnhof", key: "junction_station" },
            { kind: "number", label: "Anzahl Knotenbahnhöfe", key: "number_junction_station", indent: true },
            { kind: "switch", label: "Überholbahnhof", key: "overtaking_station" },
            { kind: "number", label: "Anzahl Überholbahnhöfe", key: "number_overtaking_station", indent: true },
            { kind: "switch", label: "Depot", key: "depot" },
            { kind: "switch", label: "Niveaufreier Bahnsteigzugang", key: "level_free_platform_entrance" },
            { kind: "switch", label: "Doppelbelegung", key: "double_occupancy" },
            { kind: "switch", label: "Gleichzeitige Einfahrten", key: "simultaneous_train_entries" },
            { kind: "switch", label: "Puffergleis", key: "buffer_track" },
            { kind: "switch", label: "Überführung", key: "overpass" },
            { kind: "switch", label: "Lärmschutzwand", key: "noise_barrier" },
            { kind: "switch", label: "Bahnübergang", key: "railroad_crossing" },
            { kind: "switch", label: "Gleiswechselbetrieb (GWB)", key: "gwb" },
        ],
    },
    {
        label: "Signaltechnik & Digitalisierung",
        fields: [
            { kind: "switch", label: "ETCS", key: "etcs" },
            { kind: "number", label: "ETCS-Level", key: "etcs_level", indent: true },
            { kind: "switch", label: "Neues ESTW", key: "new_estw" },
            { kind: "switch", label: "Neues DSTW", key: "new_dstw" },
            { kind: "switch", label: "Blockerhöhung", key: "block_increase" },
            { kind: "switch", label: "Bahnhofsweichen", key: "station_railroad_switches" },
            { kind: "switch", label: "Überwerfungsbauwerk", key: "flying_junction" },
        ],
    },
    {
        label: "Elektrifizierung & Energie",
        fields: [
            { kind: "switch", label: "Elektrifizierung", key: "elektrification" },
            { kind: "switch", label: "Optimierte Elektrifizierung", key: "optimised_electrification" },
            { kind: "switch", label: "Ladestation", key: "charging_station" },
            { kind: "switch", label: "Kleine Ladestation", key: "small_charging_station" },
            { kind: "switch", label: "Batterie", key: "battery" },
            { kind: "switch", label: "Wasserstoff (H₂)", key: "h2" },
            { kind: "switch", label: "E-Fuel", key: "efuel" },
            { kind: "switch", label: "Tankstellen E-Fuel", key: "filling_stations_efuel" },
            { kind: "switch", label: "Tankstellen H₂", key: "filling_stations_h2" },
            { kind: "switch", label: "Tankstellen Diesel", key: "filling_stations_diesel" },
            { kind: "number", label: "Anzahl Tankstellen", key: "filling_stations_count" },
        ],
    },
    {
        label: "Sonstiges",
        fields: [
            { kind: "switch", label: "SGV 740m", key: "sgv740m" },
            { kind: "switch", label: "Sanierung", key: "sanierung" },
            { kind: "switch", label: "Stilllegung", key: "closure" },
        ],
    },
];

function SwitchField({
    label,
    fieldKey,
    values,
    setValues,
}: {
    label: string;
    fieldKey: BoolKey;
    values: ProjectEditFormValues;
    setValues: React.Dispatch<React.SetStateAction<ProjectEditFormValues>>;
}) {
    return (
        <Switch
            label={label}
            checked={values[fieldKey]}
            onChange={(event) => {
                const checked = event.currentTarget.checked;
                setValues((prev) => ({ ...prev, [fieldKey]: checked }));
            }}
        />
    );
}

function NumberField({
    label,
    fieldKey,
    indent,
    values,
    setValues,
}: {
    label: string;
    fieldKey: NumKey;
    indent?: boolean;
    values: ProjectEditFormValues;
    setValues: React.Dispatch<React.SetStateAction<ProjectEditFormValues>>;
}) {
    return (
        <NumberInput
            label={label}
            value={values[fieldKey] ?? ""}
            onChange={(value) =>
                setValues((prev) => ({
                    ...prev,
                    [fieldKey]: typeof value === "number" ? value : null,
                }))
            }
            min={0}
            ml={indent ? "xl" : undefined}
        />
    );
}

export function ProjectEditFields({ values, setValues, geojson }: ProjectEditFieldsProps) {
    const { data: groups = [] } = useProjectGroups();
    const projectGroupOptions = useMemo(
        () => groups.map((g) => ({ value: String(g.id), label: g.name })),
        [groups],
    );

    const [search, setSearch] = useState("");
    const query = search.trim().toLowerCase();
    const matches = (label: string) => query === "" || label.toLowerCase().includes(query);

    const hasLineGeometry = !!geojson;

    const handleComputeLength = () => {
        const km = computeGeojsonLengthKm(geojson);
        if (km == null) {
            notifications.show({
                color: "yellow",
                title: "Keine Linien-Geometrie",
                message: "Aus der Projektgeometrie konnte keine Länge berechnet werden.",
            });
            return;
        }
        setValues((prev) => ({ ...prev, length: km }));
        notifications.show({
            color: "green",
            title: "Länge berechnet",
            message: `Länge aus der Geometrie: ${km.toLocaleString("de-DE")} km`,
        });
    };

    const renderField = (field: PropField) =>
        field.kind === "switch" ? (
            <SwitchField key={field.key} label={field.label} fieldKey={field.key} values={values} setValues={setValues} />
        ) : (
            <NumberField
                key={field.key}
                label={field.label}
                fieldKey={field.key}
                indent={field.indent}
                values={values}
                setValues={setValues}
            />
        );

    return (
        <Stack gap="md">
            <Divider label="Stammdaten" labelPosition="left" />

            <TextInput
                label="Projektname"
                required
                value={values.name}
                onChange={(event) => {
                    const value = event.currentTarget.value;
                    setValues((prev) => ({ ...prev, name: value }));
                }}
            />

            <TextInput
                label="Projektnummer"
                placeholder="z. B. ABS 123"
                value={values.project_number ?? ""}
                onChange={(event) => {
                    const value = event.currentTarget.value;
                    setValues((prev) => ({ ...prev, project_number: value || null }));
                }}
            />

            <div>
                <NumberInput
                    label="Länge in Kilometern"
                    placeholder="z. B. 42,5"
                    value={values.length ?? ""}
                    onChange={(value) =>
                        setValues((prev) => ({
                            ...prev,
                            length: typeof value === "number" ? value : null,
                        }))
                    }
                    decimalScale={2}
                    min={0}
                />
                {hasLineGeometry && (
                    <Button size="xs" variant="light" mt={6} onClick={handleComputeLength}>
                        Aus Geometrie berechnen
                    </Button>
                )}
            </div>

            <Textarea
                label="Beschreibung"
                minRows={3}
                autosize
                value={values.description ?? ""}
                onChange={(event) => {
                    const value = event.currentTarget.value;
                    setValues((prev) => ({ ...prev, description: value || null }));
                }}
            />

            <Textarea
                label="Begründung"
                minRows={2}
                autosize
                value={values.justification ?? ""}
                onChange={(event) => {
                    const value = event.currentTarget.value;
                    setValues((prev) => ({ ...prev, justification: value || null }));
                }}
            />

            <MultiSelect
                label="Projektgruppen"
                placeholder="Gruppen auswählen…"
                data={projectGroupOptions}
                value={values.project_group_ids.map(String)}
                onChange={(selected) =>
                    setValues((prev) => ({
                        ...prev,
                        project_group_ids: selected
                            .map((s) => parseInt(s, 10))
                            .filter((n) => !isNaN(n)),
                    }))
                }
                searchable
                clearable
            />

            <Divider label="Eigenschaften" labelPosition="left" />
            <TextInput
                placeholder="Eigenschaft suchen… (z. B. ETCS, Tunnel, Bahnsteig)"
                value={search}
                onChange={(event) => setSearch(event.currentTarget.value)}
            />

            {(() => {
                const visibleSections = PROPERTY_SECTIONS.map((section) => ({
                    label: section.label,
                    fields: section.fields.filter((f) => matches(f.label)),
                })).filter((section) => section.fields.length > 0);

                if (visibleSections.length === 0) {
                    return (
                        <Text c="dimmed" size="sm">
                            Keine Eigenschaft passt zu „{search}".
                        </Text>
                    );
                }

                return visibleSections.map((section) => (
                    <Fragment key={section.label}>
                        <Divider label={section.label} labelPosition="left" />
                        <Stack gap="xs">{section.fields.map(renderField)}</Stack>
                    </Fragment>
                ));
            })()}
        </Stack>
    );
}

export default ProjectEditFields;
