import { useEffect, useMemo, useState } from "react";
import {
    Alert,
    Box,
    Button,
    Drawer,
    Group,
    ScrollArea,
} from "@mantine/core";

import type { Project } from "../../shared/api/queries";
import { useProjectGroups } from "../../shared/api/queries";
import { ProjectEditFields } from "./ProjectEditFields";

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

export function createInitialValues(project: Project): ProjectEditFormValues {
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
                <ProjectEditFields values={values} setValues={setValues} projectGroupOptions={groupOptions} />
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
