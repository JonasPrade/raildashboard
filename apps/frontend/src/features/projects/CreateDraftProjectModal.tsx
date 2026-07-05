import { useEffect, useState } from "react";
import { Alert, Button, Group, Modal, Stack, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconInfoCircle } from "@tabler/icons-react";

import { useCreateProject, type Project } from "../../shared/api/queries";
import ProjectSearchSelect from "./ProjectSearchSelect";

type Props = {
    opened: boolean;
    onClose: () => void;
    /** Pre-fills the project name (e.g. the raw importer title). */
    initialName?: string;
    /** Pre-selects a superior project (e.g. an already-matched parent). */
    initialSuperiorId?: number | null;
    /** Human-readable source the draft will be linked to ("DB-Bauportal" …). */
    sourceLabel?: string;
    /** Called with the created draft so the caller can link it to its entry. */
    onCreated: (project: Project) => void;
};

/**
 * Reusable "a project is missing → note it for creation" dialog. Creates the
 * project immediately as a draft (``is_draft = true``, hidden from the public
 * list/map, editable under /admin/drafts) with an optional superior project,
 * then hands the created draft back so the caller can link it to the importer
 * entry (Bauportal / Fulda-Runde / Haushalt). Finalize it later on the drafts
 * board.
 */
export default function CreateDraftProjectModal({
    opened,
    onClose,
    initialName,
    initialSuperiorId = null,
    sourceLabel,
    onCreated,
}: Props) {
    const create = useCreateProject();
    const [name, setName] = useState(initialName ?? "");
    const [superiorId, setSuperiorId] = useState<number | null>(initialSuperiorId);

    // Re-seed the fields whenever the dialog is (re-)opened for a new entry.
    useEffect(() => {
        if (opened) {
            setName(initialName ?? "");
            setSuperiorId(initialSuperiorId);
        }
    }, [opened, initialName, initialSuperiorId]);

    const handleSubmit = () => {
        const trimmed = name.trim();
        if (!trimmed) return;
        create.mutate(
            { name: trimmed, is_draft: true, superior_project_id: superiorId },
            {
                onSuccess: (project) => {
                    notifications.show({
                        color: "green",
                        title: "Als Entwurf gespeichert",
                        message: `„${project.name}" wurde als Projektentwurf angelegt und verknüpft.`,
                    });
                    onCreated(project);
                    onClose();
                },
                onError: () =>
                    notifications.show({
                        color: "red",
                        title: "Fehler",
                        message: "Der Projektentwurf konnte nicht angelegt werden.",
                    }),
            },
        );
    };

    return (
        <Modal opened={opened} onClose={onClose} title="Projekt als Entwurf anlegen" size="lg" centered>
            <Stack gap="md">
                <Alert variant="light" color="blue" icon={<IconInfoCircle size={16} />}>
                    Das Projekt wird als <strong>Entwurf</strong> gespeichert und
                    {sourceLabel ? ` mit dem ${sourceLabel}-Eintrag verknüpft` : " mit dem Eintrag verknüpft"}.
                    Du kannst es später unter <strong>Verwaltung → Entwürfe</strong> vervollständigen und finalisieren.
                </Alert>

                <TextInput
                    label="Projektname"
                    placeholder="Name des fehlenden Projekts"
                    value={name}
                    onChange={(e) => setName(e.currentTarget.value)}
                    required
                    data-autofocus
                />

                <ProjectSearchSelect
                    label="Überprojekt (optional)"
                    value={superiorId}
                    onChange={setSuperiorId}
                />

                <Group justify="flex-end" gap="sm">
                    <Button variant="subtle" color="gray" onClick={onClose}>
                        Abbrechen
                    </Button>
                    <Button onClick={handleSubmit} loading={create.isPending} disabled={!name.trim()}>
                        Entwurf anlegen & verknüpfen
                    </Button>
                </Group>
            </Stack>
        </Modal>
    );
}
