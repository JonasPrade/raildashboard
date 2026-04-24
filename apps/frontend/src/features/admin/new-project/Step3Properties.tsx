import { Alert, Button, Group, Stack, Text } from "@mantine/core";
import { useState } from "react";

import { updateProject, type Project } from "../../../shared/api/queries";
import {
    createInitialValues,
    createUpdatePayload,
    type ProjectEditFormValues,
} from "../../projects/ProjectEdit";
import { ProjectEditFields } from "../../projects/ProjectEditFields";

type Props = {
    project: Project;
    onDone: (updated: Project) => void;
};

export default function Step3Properties({ project, onDone }: Props) {
    const [values, setValues] = useState<ProjectEditFormValues>(() => createInitialValues(project));
    const [saving, setSaving] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const handleSave = async () => {
        if (project.id == null) return;
        setSaving(true);
        setErrorMessage(null);
        try {
            const updated = await updateProject(project.id, createUpdatePayload(values));
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
            <ProjectEditFields values={values} setValues={setValues} />
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
