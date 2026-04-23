import { Alert, Button, Group, Stack, Text } from "@mantine/core";
import { useMemo, useState } from "react";

import {
    updateProject,
    useProjectGroups,
    type Project,
    type ProjectUpdatePayload,
} from "../../../shared/api/queries";
import {
    createInitialValues,
    type ProjectEditFormValues,
} from "../../projects/ProjectEdit";
import { ProjectEditFields } from "../../projects/ProjectEditFields";

type Props = {
    project: Project;
    onDone: (updated: Project) => void;
};

function buildUpdatePayload(values: ProjectEditFormValues): ProjectUpdatePayload {
    return {
        name: values.name,
        project_number: values.project_number,
        description: values.description,
        justification: values.justification,
        length: values.length,
        new_vmax: values.new_vmax,
        etcs_level: values.etcs_level,
        number_junction_station: values.number_junction_station,
        number_overtaking_station: values.number_overtaking_station,
        filling_stations_count: values.filling_stations_count,
        effects_passenger_long_rail: values.effects_passenger_long_rail,
        effects_passenger_local_rail: values.effects_passenger_local_rail,
        effects_cargo_rail: values.effects_cargo_rail,
        nbs: values.nbs,
        abs: values.abs,
        second_track: values.second_track,
        third_track: values.third_track,
        fourth_track: values.fourth_track,
        curve: values.curve,
        increase_speed: values.increase_speed,
        tunnel_structural_gauge: values.tunnel_structural_gauge,
        tilting: values.tilting,
        new_station: values.new_station,
        platform: values.platform,
        junction_station: values.junction_station,
        overtaking_station: values.overtaking_station,
        depot: values.depot,
        level_free_platform_entrance: values.level_free_platform_entrance,
        double_occupancy: values.double_occupancy,
        simultaneous_train_entries: values.simultaneous_train_entries,
        buffer_track: values.buffer_track,
        overpass: values.overpass,
        noise_barrier: values.noise_barrier,
        railroad_crossing: values.railroad_crossing,
        gwb: values.gwb,
        etcs: values.etcs,
        new_estw: values.new_estw,
        new_dstw: values.new_dstw,
        block_increase: values.block_increase,
        station_railroad_switches: values.station_railroad_switches,
        flying_junction: values.flying_junction,
        elektrification: values.elektrification,
        optimised_electrification: values.optimised_electrification,
        charging_station: values.charging_station,
        small_charging_station: values.small_charging_station,
        battery: values.battery,
        h2: values.h2,
        efuel: values.efuel,
        filling_stations_efuel: values.filling_stations_efuel,
        filling_stations_h2: values.filling_stations_h2,
        filling_stations_diesel: values.filling_stations_diesel,
        sgv740m: values.sgv740m,
        sanierung: values.sanierung,
        closure: values.closure,
        project_group_ids: values.project_group_ids,
    };
}

export default function Step3Properties({ project, onDone }: Props) {
    const { data: groups = [] } = useProjectGroups();
    const groupOptions = useMemo(
        () => groups.map((g) => ({ value: String(g.id), label: g.name })),
        [groups],
    );
    const [values, setValues] = useState<ProjectEditFormValues>(() => createInitialValues(project));
    const [saving, setSaving] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const handleSave = async () => {
        if (project.id == null) return;
        setSaving(true);
        setErrorMessage(null);
        try {
            const updated = await updateProject(project.id, buildUpdatePayload(values));
            onDone(updated);
        } catch (err) {
            setErrorMessage((err as Error)?.message ?? "Unbekannter Fehler");
        } finally {
            setSaving(false);
        }
    };

    return (
        <Stack gap="md">
            <Text c="dimmed" size="sm">
                Projekteigenschaften für dieses Projekt setzen (optional).
            </Text>
            <ProjectEditFields
                values={values}
                setValues={setValues}
                projectGroupOptions={groupOptions}
            />
            {errorMessage && (
                <Alert color="red" variant="light" title="Speichern fehlgeschlagen">
                    {errorMessage}
                </Alert>
            )}
            <Group justify="flex-end">
                <Button variant="subtle" onClick={() => onDone(project)} disabled={saving}>
                    Überspringen
                </Button>
                <Button onClick={handleSave} loading={saving}>
                    Speichern & Weiter
                </Button>
            </Group>
        </Stack>
    );
}
