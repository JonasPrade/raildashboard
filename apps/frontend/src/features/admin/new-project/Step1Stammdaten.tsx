import { Alert, Button, Group, MultiSelect, Stack, TextInput, Textarea } from "@mantine/core";
import { useMemo, useState } from "react";

import {
    updateProject,
    useCreateProject,
    useProjectGroups,
    type Project,
    type ProjectCreatePayload,
} from "../../../shared/api/queries";
import ProjectSearchSelect from "../../projects/ProjectSearchSelect";

type Props = {
    /** When set, the step edits this existing draft (PATCH) instead of creating a new one. */
    project?: Project | null;
    onCreated: (project: Project) => void;
};

export default function Step1Stammdaten({ project, onCreated }: Props) {
    const isEdit = project != null;
    const createProject = useCreateProject();
    const { data: groups = [] } = useProjectGroups();
    const [name, setName] = useState(project?.name ?? "");
    const [projectNumber, setProjectNumber] = useState(project?.project_number ?? "");
    const [description, setDescription] = useState(project?.description ?? "");
    const [justification, setJustification] = useState(project?.justification ?? "");
    const [superiorId, setSuperiorId] = useState<number | null>(project?.superior_project_id ?? null);
    const [groupIds, setGroupIds] = useState<string[]>(
        (project?.project_groups ?? []).map((g) => String(g.id)),
    );
    const [saving, setSaving] = useState(false);
    const [editError, setEditError] = useState<string | null>(null);

    const groupOptions = useMemo(
        () => groups.map((g) => ({ value: String(g.id), label: g.name })),
        [groups],
    );

    const pending = createProject.isPending || saving;
    const disabled = name.trim().length === 0 || pending;

    const handleSubmit = async () => {
        if (isEdit && project?.id != null) {
            setEditError(null);
            setSaving(true);
            try {
                const updated = await updateProject(project.id, {
                    name: name.trim(),
                    project_number: projectNumber || null,
                    description: description || null,
                    justification: justification || null,
                    superior_project_id: superiorId,
                    project_group_ids: groupIds.map(Number),
                });
                onCreated(updated);
            } catch (e) {
                setEditError((e as Error | null)?.message ?? "Unbekannter Fehler");
            } finally {
                setSaving(false);
            }
            return;
        }

        const payload: ProjectCreatePayload = {
            name: name.trim(),
            is_draft: true,
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
            /* surfaced via createProject.error */
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
            {(createProject.isError || editError) && (
                <Alert color="red" variant="light" title="Speichern fehlgeschlagen">
                    {editError ?? (createProject.error as Error | null)?.message ?? "Unbekannter Fehler"}
                </Alert>
            )}
            <Group justify="flex-end">
                <Button onClick={handleSubmit} disabled={disabled} loading={pending}>
                    {isEdit ? "Speichern & Weiter" : "Projekt anlegen"}
                </Button>
            </Group>
        </Stack>
    );
}
