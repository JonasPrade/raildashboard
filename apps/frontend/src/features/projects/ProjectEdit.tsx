import { useEffect, useMemo, useState } from "react";
import {
    Alert,
    Box,
    Button,
    Divider,
    Drawer,
    Group,
    MultiSelect,
    NumberInput,
    ScrollArea,
    Stack,
    Switch,
    Textarea,
    TextInput,
} from "@mantine/core";

import type { Project } from "../../shared/api/queries";
import { useProjectGroups } from "../../shared/api/queries";

export type ProjectEditFormValues = {
    // Text fields
    name: string;
    project_number: string | null;
    description: string | null;
    justification: string | null;
    // Numeric fields
    length: number | null;
    new_vmax: number | null;
    etcs_level: number | null;
    number_junction_station: number | null;
    number_overtaking_station: number | null;
    filling_stations_count: number | null;
    // Train categories
    effects_passenger_long_rail: boolean;
    effects_passenger_local_rail: boolean;
    effects_cargo_rail: boolean;
    // Streckenausbau
    nbs: boolean;
    abs: boolean;
    second_track: boolean;
    third_track: boolean;
    fourth_track: boolean;
    curve: boolean;
    increase_speed: boolean;
    tunnel_structural_gauge: boolean;
    tilting: boolean;
    // Bahnhöfe & Infrastruktur
    new_station: boolean;
    platform: boolean;
    junction_station: boolean;
    overtaking_station: boolean;
    depot: boolean;
    level_free_platform_entrance: boolean;
    double_occupancy: boolean;
    simultaneous_train_entries: boolean;
    buffer_track: boolean;
    overpass: boolean;
    noise_barrier: boolean;
    railroad_crossing: boolean;
    gwb: boolean;
    // Signaltechnik & Digitalisierung
    etcs: boolean;
    new_estw: boolean;
    new_dstw: boolean;
    block_increase: boolean;
    station_railroad_switches: boolean;
    flying_junction: boolean;
    // Elektrifizierung & Energie
    elektrification: boolean;
    optimised_electrification: boolean;
    charging_station: boolean;
    small_charging_station: boolean;
    battery: boolean;
    h2: boolean;
    efuel: boolean;
    filling_stations_efuel: boolean;
    filling_stations_h2: boolean;
    filling_stations_diesel: boolean;
    // Sonstiges
    sgv740m: boolean;
    sanierung: boolean;
    closure: boolean;
    // Projektgruppen
    project_group_ids: number[];
};

type ProjectEditProps = {
    project: Project;
    opened: boolean;
    onClose: () => void;
    onSubmit: (values: ProjectEditFormValues) => void;
    isSubmitting?: boolean;
    errorMessage?: string;
};

function b(v: boolean | null | undefined): boolean {
    return Boolean(v);
}

function createInitialValues(project: Project): ProjectEditFormValues {
    return {
        name: project.name,
        project_number: project.project_number ?? null,
        description: project.description ?? null,
        justification: project.justification ?? null,
        length: project.length ?? null,
        new_vmax: project.new_vmax ?? null,
        etcs_level: project.etcs_level ?? null,
        number_junction_station: project.number_junction_station ?? null,
        number_overtaking_station: project.number_overtaking_station ?? null,
        filling_stations_count: project.filling_stations_count ?? null,
        effects_passenger_long_rail: b(project.effects_passenger_long_rail),
        effects_passenger_local_rail: b(project.effects_passenger_local_rail),
        effects_cargo_rail: b(project.effects_cargo_rail),
        nbs: b(project.nbs),
        abs: b(project.abs),
        second_track: b(project.second_track),
        third_track: b(project.third_track),
        fourth_track: b(project.fourth_track),
        curve: b(project.curve),
        increase_speed: b(project.increase_speed),
        tunnel_structural_gauge: b(project.tunnel_structural_gauge),
        tilting: b(project.tilting),
        new_station: b(project.new_station),
        platform: b(project.platform),
        junction_station: b(project.junction_station),
        overtaking_station: b(project.overtaking_station),
        depot: b(project.depot),
        level_free_platform_entrance: b(project.level_free_platform_entrance),
        double_occupancy: b(project.double_occupancy),
        simultaneous_train_entries: b(project.simultaneous_train_entries),
        buffer_track: b(project.buffer_track),
        overpass: b(project.overpass),
        noise_barrier: b(project.noise_barrier),
        railroad_crossing: b(project.railroad_crossing),
        gwb: b(project.gwb),
        etcs: b(project.etcs),
        new_estw: b(project.new_estw),
        new_dstw: b(project.new_dstw),
        block_increase: b(project.block_increase),
        station_railroad_switches: b(project.station_railroad_switches),
        flying_junction: b(project.flying_junction),
        elektrification: b(project.elektrification),
        optimised_electrification: b(project.optimised_electrification),
        charging_station: b(project.charging_station),
        small_charging_station: b(project.small_charging_station),
        battery: b(project.battery),
        h2: b(project.h2),
        efuel: b(project.efuel),
        filling_stations_efuel: b(project.filling_stations_efuel),
        filling_stations_h2: b(project.filling_stations_h2),
        filling_stations_diesel: b(project.filling_stations_diesel),
        sgv740m: b(project.sgv740m),
        sanierung: b(project.sanierung),
        closure: b(project.closure),
        project_group_ids: (project.project_groups ?? []).map((g) => g.id),
    };
}

function SwitchField({
    label,
    fieldKey,
    values,
    setValues,
}: {
    label: string;
    fieldKey: keyof ProjectEditFormValues;
    values: ProjectEditFormValues;
    setValues: React.Dispatch<React.SetStateAction<ProjectEditFormValues>>;
}) {
    return (
        <Switch
            label={label}
            checked={values[fieldKey] as boolean}
            onChange={(event) => {
                const checked = event.currentTarget.checked;
                setValues((prev) => ({ ...prev, [fieldKey]: checked }));
            }}
        />
    );
}

export function ProjectEdit({
    project,
    opened,
    onClose,
    onSubmit,
    isSubmitting = false,
    errorMessage,
}: ProjectEditProps) {
    const [values, setValues] = useState<ProjectEditFormValues>(() => createInitialValues(project));
    const { data: allGroups = [] } = useProjectGroups();

    const initialValues = useMemo(() => createInitialValues(project), [project]);
    const groupOptions = useMemo(
        () => allGroups.map((g) => ({ value: String(g.id), label: g.name })),
        [allGroups],
    );

    const hasChanges = useMemo(() => {
        return (Object.keys(initialValues) as Array<keyof ProjectEditFormValues>).some((key) => {
            if (key === "project_group_ids") {
                const aSet = new Set(values.project_group_ids);
                const bSet = new Set(initialValues.project_group_ids);
                return aSet.size !== bSet.size || [...aSet].some((id) => !bSet.has(id));
            }
            return values[key] !== initialValues[key];
        });
    }, [initialValues, values]);

    useEffect(() => {
        if (opened) {
            setValues(createInitialValues(project));
        }
    }, [opened, project]);

    return (
        <Drawer
            opened={opened}
            onClose={onClose}
            title="Projekt bearbeiten"
            overlayProps={{ opacity: 0.4, blur: 4 }}
            position="right"
            size="xl"
            styles={{ body: { display: "flex", flexDirection: "column", height: "100%", padding: 0 } }}
        >
            <ScrollArea style={{ flex: 1 }} p="md">
            <Stack gap="md">
                {/* Stammdaten */}
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
                    data={groupOptions}
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

                {/* Verkehrsarten */}
                <Divider label="Verkehrsarten" labelPosition="left" />
                <Stack gap="xs">
                    <SwitchField label="Fernverkehr" fieldKey="effects_passenger_long_rail" values={values} setValues={setValues} />
                    <SwitchField label="Nahverkehr" fieldKey="effects_passenger_local_rail" values={values} setValues={setValues} />
                    <SwitchField label="Güterverkehr" fieldKey="effects_cargo_rail" values={values} setValues={setValues} />
                </Stack>

                {/* Streckenausbau */}
                <Divider label="Streckenausbau" labelPosition="left" />
                <Stack gap="xs">
                    <SwitchField label="Neubaustrecke (NBS)" fieldKey="nbs" values={values} setValues={setValues} />
                    <SwitchField label="Ausbaustrecke (ABS)" fieldKey="abs" values={values} setValues={setValues} />
                    <SwitchField label="Zweigleisiger Ausbau" fieldKey="second_track" values={values} setValues={setValues} />
                    <SwitchField label="Dreigleisiger Ausbau" fieldKey="third_track" values={values} setValues={setValues} />
                    <SwitchField label="Viergleisiger Ausbau" fieldKey="fourth_track" values={values} setValues={setValues} />
                    <SwitchField label="Kurvenanhebung" fieldKey="curve" values={values} setValues={setValues} />
                    <SwitchField label="Geschwindigkeitsanhebung" fieldKey="increase_speed" values={values} setValues={setValues} />
                    <NumberInput
                        label="Neue Vmax (km/h)"
                        value={values.new_vmax ?? ""}
                        onChange={(value) =>
                            setValues((prev) => ({
                                ...prev,
                                new_vmax: typeof value === "number" ? value : null,
                            }))
                        }
                        min={0}
                        ml="xl"
                    />
                    <SwitchField label="Tunnel Lichtraumprofil" fieldKey="tunnel_structural_gauge" values={values} setValues={setValues} />
                    <SwitchField label="Neigetechnik" fieldKey="tilting" values={values} setValues={setValues} />
                </Stack>

                {/* Bahnhöfe & Infrastruktur */}
                <Divider label="Bahnhöfe & Infrastruktur" labelPosition="left" />
                <Stack gap="xs">
                    <SwitchField label="Neuer Bahnhof" fieldKey="new_station" values={values} setValues={setValues} />
                    <SwitchField label="Bahnsteig" fieldKey="platform" values={values} setValues={setValues} />
                    <SwitchField label="Knotenbahnhof" fieldKey="junction_station" values={values} setValues={setValues} />
                    <NumberInput
                        label="Anzahl Knotenbahnhöfe"
                        value={values.number_junction_station ?? ""}
                        onChange={(value) =>
                            setValues((prev) => ({
                                ...prev,
                                number_junction_station: typeof value === "number" ? value : null,
                            }))
                        }
                        min={0}
                        ml="xl"
                    />
                    <SwitchField label="Überholbahnhof" fieldKey="overtaking_station" values={values} setValues={setValues} />
                    <NumberInput
                        label="Anzahl Überholbahnhöfe"
                        value={values.number_overtaking_station ?? ""}
                        onChange={(value) =>
                            setValues((prev) => ({
                                ...prev,
                                number_overtaking_station: typeof value === "number" ? value : null,
                            }))
                        }
                        min={0}
                        ml="xl"
                    />
                    <SwitchField label="Depot" fieldKey="depot" values={values} setValues={setValues} />
                    <SwitchField label="Niveaufreier Bahnsteigzugang" fieldKey="level_free_platform_entrance" values={values} setValues={setValues} />
                    <SwitchField label="Doppelbelegung" fieldKey="double_occupancy" values={values} setValues={setValues} />
                    <SwitchField label="Gleichzeitige Einfahrten" fieldKey="simultaneous_train_entries" values={values} setValues={setValues} />
                    <SwitchField label="Puffergleis" fieldKey="buffer_track" values={values} setValues={setValues} />
                    <SwitchField label="Überführung" fieldKey="overpass" values={values} setValues={setValues} />
                    <SwitchField label="Lärmschutzwand" fieldKey="noise_barrier" values={values} setValues={setValues} />
                    <SwitchField label="Bahnübergang" fieldKey="railroad_crossing" values={values} setValues={setValues} />
                    <SwitchField label="Gleiswechselbetrieb (GWB)" fieldKey="gwb" values={values} setValues={setValues} />
                </Stack>

                {/* Signaltechnik & Digitalisierung */}
                <Divider label="Signaltechnik & Digitalisierung" labelPosition="left" />
                <Stack gap="xs">
                    <SwitchField label="ETCS" fieldKey="etcs" values={values} setValues={setValues} />
                    <NumberInput
                        label="ETCS-Level"
                        value={values.etcs_level ?? ""}
                        onChange={(value) =>
                            setValues((prev) => ({
                                ...prev,
                                etcs_level: typeof value === "number" ? value : null,
                            }))
                        }
                        min={0}
                        ml="xl"
                    />
                    <SwitchField label="Neues ESTW" fieldKey="new_estw" values={values} setValues={setValues} />
                    <SwitchField label="Neues DSTW" fieldKey="new_dstw" values={values} setValues={setValues} />
                    <SwitchField label="Blockerhöhung" fieldKey="block_increase" values={values} setValues={setValues} />
                    <SwitchField label="Bahnhofsweichen" fieldKey="station_railroad_switches" values={values} setValues={setValues} />
                    <SwitchField label="Überwerfungsbauwerk" fieldKey="flying_junction" values={values} setValues={setValues} />
                </Stack>

                {/* Elektrifizierung & Energie */}
                <Divider label="Elektrifizierung & Energie" labelPosition="left" />
                <Stack gap="xs">
                    <SwitchField label="Elektrifizierung" fieldKey="elektrification" values={values} setValues={setValues} />
                    <SwitchField label="Optimierte Elektrifizierung" fieldKey="optimised_electrification" values={values} setValues={setValues} />
                    <SwitchField label="Ladestation" fieldKey="charging_station" values={values} setValues={setValues} />
                    <SwitchField label="Kleine Ladestation" fieldKey="small_charging_station" values={values} setValues={setValues} />
                    <SwitchField label="Batterie" fieldKey="battery" values={values} setValues={setValues} />
                    <SwitchField label="Wasserstoff (H₂)" fieldKey="h2" values={values} setValues={setValues} />
                    <SwitchField label="E-Fuel" fieldKey="efuel" values={values} setValues={setValues} />
                    <SwitchField label="Tankstellen E-Fuel" fieldKey="filling_stations_efuel" values={values} setValues={setValues} />
                    <SwitchField label="Tankstellen H₂" fieldKey="filling_stations_h2" values={values} setValues={setValues} />
                    <SwitchField label="Tankstellen Diesel" fieldKey="filling_stations_diesel" values={values} setValues={setValues} />
                    <NumberInput
                        label="Anzahl Tankstellen"
                        value={values.filling_stations_count ?? ""}
                        onChange={(value) =>
                            setValues((prev) => ({
                                ...prev,
                                filling_stations_count: typeof value === "number" ? value : null,
                            }))
                        }
                        min={0}
                        ml="xl"
                    />
                </Stack>

                {/* Sonstiges */}
                <Divider label="Sonstiges" labelPosition="left" />
                <Stack gap="xs">
                    <SwitchField label="SGV 740m" fieldKey="sgv740m" values={values} setValues={setValues} />
                    <SwitchField label="Sanierung" fieldKey="sanierung" values={values} setValues={setValues} />
                    <SwitchField label="Stilllegung" fieldKey="closure" values={values} setValues={setValues} />
                </Stack>

            </Stack>
            </ScrollArea>

            <Box p="md" style={{ borderTop: "1px solid var(--mantine-color-default-border)" }}>
                {errorMessage && (
                    <Alert color="red" variant="light" title="Speichern fehlgeschlagen" mb="sm">
                        {errorMessage}
                    </Alert>
                )}
                <Group justify="flex-end">
                    <Button variant="default" onClick={onClose} disabled={isSubmitting}>
                        Abbrechen
                    </Button>
                    <Button
                        onClick={() => onSubmit(values)}
                        loading={isSubmitting}
                        disabled={!hasChanges || values.name.trim() === ""}
                    >
                        Speichern
                    </Button>
                </Group>
            </Box>
        </Drawer>
    );
}

export default ProjectEdit;
