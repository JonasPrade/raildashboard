import { Alert, Button, Group, Select, Stack, Text } from "@mantine/core";
import { useState } from "react";

import { updateProject, updateProjectProgress, type Project } from "../../../shared/api/queries";
import {
    createInitialValues,
    createUpdatePayload,
    type ProjectEditFormValues,
} from "../../projects/ProjectEdit";
import { ProjectEditFields } from "../../projects/ProjectEditFields";
import { MAIN_PHASES, MAIN_PHASE_LABEL, type MainPhase } from "../../projects/components/progress/phaseMeta";

const PHASE_NONE = "__none__";

type Props = {
    project: Project;
    onDone: (updated: Project) => void;
};

export default function Step3Properties({ project, onDone }: Props) {
    const [values, setValues] = useState<ProjectEditFormValues>(() => createInitialValues(project));
    const [phase, setPhase] = useState<MainPhase | null>(null);
    const [saving, setSaving] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const handleSave = async () => {
        if (project.id == null) return;
        setSaving(true);
        setErrorMessage(null);
        try {
            const updated = await updateProject(project.id, createUpdatePayload(values));
            if (phase !== null) {
                await updateProjectProgress(project.id, { manual_phase_override: phase });
            }
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
            <Select
                label="Planungsphase"
                description="Setzt den aktuellen Planungsstand des Projekts (optional, später im Planungsstand änderbar)."
                value={phase ?? PHASE_NONE}
                data={[
                    { value: PHASE_NONE, label: "— nicht festlegen —" },
                    ...MAIN_PHASES.map((p) => ({ value: p, label: MAIN_PHASE_LABEL[p] })),
                ]}
                onChange={(v) => setPhase(!v || v === PHASE_NONE ? null : (v as MainPhase))}
                w={280}
            />
            <ProjectEditFields values={values} setValues={setValues} geojson={project.geojson_representation} />
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
