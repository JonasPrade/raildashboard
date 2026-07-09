import { useEffect, useMemo, useState } from "react";
import {
    Alert,
    Box,
    Button,
    Drawer,
    Group,
    ScrollArea,
} from "@mantine/core";

import type { Project, ProjectUpdatePayload } from "../../shared/api/queries";
import { ProjectEditFields } from "./ProjectEditFields";
import { BOOL_KEYS, NUM_KEYS, type BoolKey, type NumKey } from "./projectPropertyFields";

/**
 * Form state: the ~8 explicit scalar/text fields plus every toggle/number
 * property derived from PROPERTY_SECTIONS (see projectPropertyFields.ts).
 */
export type ProjectEditFormValues = {
    name: string;
    project_number: string | null;
    description: string | null;
    justification: string | null;
    length: number | null;
    project_group_ids: number[];
} & Record<BoolKey, boolean> &
    Record<NumKey, number | null>;

type ProjectEditProps = {
    project: Project;
    opened: boolean;
    onClose: () => void;
    onSubmit: (values: ProjectEditFormValues) => void;
    isSubmitting?: boolean;
    errorMessage?: string;
};

export function createInitialValues(project: Project): ProjectEditFormValues {
    return {
        name: project.name,
        project_number: project.project_number ?? null,
        description: project.description ?? null,
        justification: project.justification ?? null,
        length: project.length ?? null,
        project_group_ids: (project.project_groups ?? []).map((g) => g.id),
        ...(Object.fromEntries(BOOL_KEYS.map((k) => [k, Boolean(project[k])])) as Record<
            BoolKey,
            boolean
        >),
        ...(Object.fromEntries(NUM_KEYS.map((k) => [k, project[k] ?? null])) as Record<
            NumKey,
            number | null
        >),
    };
}

export function createUpdatePayload(values: ProjectEditFormValues): ProjectUpdatePayload {
    // NumberInput can hold "" while typing — anything non-numeric becomes null.
    const num = (v: number | null) => (typeof v === "number" ? v : null);
    return {
        name: values.name.trim(),
        project_number: values.project_number?.trim() || null,
        description: values.description?.trim() || null,
        justification: values.justification?.trim() || null,
        length: num(values.length),
        project_group_ids: values.project_group_ids,
        ...(Object.fromEntries(BOOL_KEYS.map((k) => [k, values[k]])) as Record<BoolKey, boolean>),
        ...(Object.fromEntries(NUM_KEYS.map((k) => [k, num(values[k])])) as Record<
            NumKey,
            number | null
        >),
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

    const initialValues = useMemo(() => createInitialValues(project), [project]);

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
                <ProjectEditFields values={values} setValues={setValues} geojson={project.geojson_representation} />
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
