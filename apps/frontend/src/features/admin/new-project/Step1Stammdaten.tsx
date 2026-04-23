import { Alert, Button, Group, MultiSelect, Stack, TextInput, Textarea } from "@mantine/core";
import { useMemo, useState } from "react";

import {
    useCreateProject,
    useProjectGroups,
    type Project,
    type ProjectCreatePayload,
} from "../../../shared/api/queries";
import ProjectSearchSelect from "../../projects/ProjectSearchSelect";

type Props = {
    onCreated: (project: Project) => void;
};

export default function Step1Stammdaten({ onCreated }: Props) {
    const createProject = useCreateProject();
    const { data: groups = [] } = useProjectGroups();
    const [name, setName] = useState("");
    const [projectNumber, setProjectNumber] = useState("");
    const [description, setDescription] = useState("");
    const [justification, setJustification] = useState("");
    const [superiorId, setSuperiorId] = useState<number | null>(null);
    const [groupIds, setGroupIds] = useState<string[]>([]);

    const groupOptions = useMemo(
        () => groups.map((g) => ({ value: String(g.id), label: g.name })),
        [groups],
    );

    const disabled = name.trim().length === 0 || createProject.isPending;

    const handleSubmit = async () => {
        const payload: ProjectCreatePayload = {
            name: name.trim(),
            project_number: projectNumber || null,
            description: description || null,
            justification: justification || null,
            superior_project_id: superiorId,
            project_group_ids: groupIds.map(Number),
        };
        try {
            const created = await createProject.mutateAsync(payload);
            onCreated(created);
        } catch {
            // error surfaces via createProject.error
        }
    };

    return (
        <Stack gap="md">
            <TextInput
                label="Projektname"
                required
                value={name}
                onChange={(e) => setName(e.currentTarget.value)}
            />
            <TextInput
                label="Projektnummer"
                placeholder="z. B. ABS 123"
                value={projectNumber}
                onChange={(e) => setProjectNumber(e.currentTarget.value)}
            />
            <Textarea
                label="Beschreibung"
                autosize
                minRows={3}
                value={description}
                onChange={(e) => setDescription(e.currentTarget.value)}
            />
            <Textarea
                label="Begründung"
                autosize
                minRows={2}
                value={justification}
                onChange={(e) => setJustification(e.currentTarget.value)}
            />
            <ProjectSearchSelect
                label="Übergeordnetes Projekt"
                value={superiorId}
                onChange={setSuperiorId}
            />
            <MultiSelect
                label="Projektgruppen"
                data={groupOptions}
                value={groupIds}
                onChange={setGroupIds}
                searchable
                clearable
                placeholder="Gruppen auswählen…"
            />
            {createProject.isError && (
                <Alert color="red" variant="light" title="Speichern fehlgeschlagen">
                    {(createProject.error as Error | null)?.message ?? "Unbekannter Fehler"}
                </Alert>
            )}
            <Group justify="flex-end">
                <Button onClick={handleSubmit} disabled={disabled} loading={createProject.isPending}>
                    Projekt anlegen
                </Button>
            </Group>
        </Stack>
    );
}
