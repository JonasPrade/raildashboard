import {
    Divider,
    MultiSelect,
    NumberInput,
    Stack,
    Switch,
    Textarea,
    TextInput,
} from "@mantine/core";
import { useMemo } from "react";

import { useProjectGroups } from "../../shared/api/queries";
import type { ProjectEditFormValues } from "./ProjectEdit";

export type ProjectEditFieldsProps = {
    values: ProjectEditFormValues;
    setValues: React.Dispatch<React.SetStateAction<ProjectEditFormValues>>;
};

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

export function ProjectEditFields({ values, setValues }: ProjectEditFieldsProps) {
    const { data: groups = [] } = useProjectGroups();
    const projectGroupOptions = useMemo(
        () => groups.map((g) => ({ value: String(g.id), label: g.name })),
        [groups],
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

            <Divider label="Verkehrsarten" labelPosition="left" />
            <Stack gap="xs">
                <SwitchField label="Fernverkehr" fieldKey="effects_passenger_long_rail" values={values} setValues={setValues} />
                <SwitchField label="Nahverkehr" fieldKey="effects_passenger_local_rail" values={values} setValues={setValues} />
                <SwitchField label="Güterverkehr" fieldKey="effects_cargo_rail" values={values} setValues={setValues} />
            </Stack>

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

            <Divider label="Sonstiges" labelPosition="left" />
            <Stack gap="xs">
                <SwitchField label="SGV 740m" fieldKey="sgv740m" values={values} setValues={setValues} />
                <SwitchField label="Sanierung" fieldKey="sanierung" values={values} setValues={setValues} />
                <SwitchField label="Stilllegung" fieldKey="closure" values={values} setValues={setValues} />
            </Stack>
        </Stack>
    );
}

export default ProjectEditFields;
