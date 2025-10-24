import { useEffect, useMemo, useState } from "react";
import {
    Alert,
    Button,
    Drawer,
    Group,
    NumberInput,
    Stack,
    Switch,
    Textarea,
    TextInput,
} from "@mantine/core";

import type { Project } from "../../shared/api/queries";

export type ProjectEditFormValues = {
    name: string;
    project_number: string | null;
    description: string | null;
    justification: string | null;
    length: number | null;
    elektrification: boolean;
    second_track: boolean;
    new_station: boolean;
};

type ProjectEditProps = {
    project: Project;
    opened: boolean;
    onClose: () => void;
    onSubmit: (values: ProjectEditFormValues) => void;
    isSubmitting?: boolean;
    errorMessage?: string;
};

function createInitialValues(project: Project): ProjectEditFormValues {
    return {
        name: project.name,
        project_number: project.project_number ?? null,
        description: project.description ?? null,
        justification: project.justification ?? null,
        length: project.length ?? null,
        elektrification: Boolean(project.elektrification),
        second_track: Boolean(project.second_track),
        new_station: Boolean(project.new_station ?? false),
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

    const hasChanges = useMemo(() => {
        const initial = createInitialValues(project);
        return (
            values.name !== initial.name ||
            values.project_number !== initial.project_number ||
            values.description !== initial.description ||
            values.justification !== initial.justification ||
            values.length !== initial.length ||
            values.elektrification !== initial.elektrification ||
            values.second_track !== initial.second_track ||
            values.new_station !== initial.new_station
        );
    }, [project, values]);

    useEffect(() => {
        if (opened) {
            setValues(createInitialValues(project));
        }
    }, [opened, project]);

    const handleSubmit = () => {
        onSubmit(values);
    };

    return (
        <Drawer
            opened={opened}
            onClose={onClose}
            title="Projekt bearbeiten"
            overlayProps={{ opacity: 0.4, blur: 4 }}
            position="right"
            size="lg"
        >
            <Stack gap="md">
                <TextInput
                    label="Projektname"
                    required
                    value={values.name}
                    onChange={(event) =>
                        setValues((prev) => ({
                            ...prev,
                            name: event.currentTarget.value,
                        }))
                    }
                />

                <TextInput
                    label="Projektnummer"
                    placeholder="z. B. ABS 123"
                    value={values.project_number ?? ""}
                    onChange={(event) =>
                        setValues((prev) => ({
                            ...prev,
                            project_number: event.currentTarget.value ? event.currentTarget.value : null,
                        }))
                    }
                />

                <NumberInput
                    label="Länge in Kilometern"
                    placeholder="z. B. 42,5"
                    value={values.length ?? undefined}
                    onChange={(value) =>
                        setValues((prev) => ({
                            ...prev,
                            length:
                                typeof value === "number"
                                    ? value
                                    : value === "" || value === null || value === undefined
                                    ? null
                                    : Number(value),
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
                    onChange={(event) =>
                        setValues((prev) => ({
                            ...prev,
                            description: event.currentTarget.value ? event.currentTarget.value : null,
                        }))
                    }
                />

                <Textarea
                    label="Begründung"
                    minRows={2}
                    autosize
                    value={values.justification ?? ""}
                    onChange={(event) =>
                        setValues((prev) => ({
                            ...prev,
                            justification: event.currentTarget.value ? event.currentTarget.value : null,
                        }))
                    }
                />

                <Stack gap="sm">
                    <Switch
                        label="Elektrifizierung"
                        checked={values.elektrification}
                        onChange={(event) =>
                            setValues((prev) => ({
                                ...prev,
                                elektrification: event.currentTarget.checked,
                            }))
                        }
                    />
                    <Switch
                        label="Zweigleisiger Ausbau"
                        checked={values.second_track}
                        onChange={(event) =>
                            setValues((prev) => ({
                                ...prev,
                                second_track: event.currentTarget.checked,
                            }))
                        }
                    />
                    <Switch
                        label="Neuer Bahnhof"
                        checked={values.new_station}
                        onChange={(event) =>
                            setValues((prev) => ({
                                ...prev,
                                new_station: event.currentTarget.checked,
                            }))
                        }
                    />
                </Stack>

                {errorMessage && (
                    <Alert color="red" variant="light" title="Speichern fehlgeschlagen">
                        {errorMessage}
                    </Alert>
                )}

                <Group justify="flex-end">
                    <Button variant="default" onClick={onClose} disabled={isSubmitting}>
                        Abbrechen
                    </Button>
                    <Button
                        onClick={handleSubmit}
                        loading={isSubmitting}
                        disabled={!hasChanges || values.name.trim() === ""}
                    >
                        Speichern
                    </Button>
                </Group>
            </Stack>
        </Drawer>
    );
}

export default ProjectEdit;
