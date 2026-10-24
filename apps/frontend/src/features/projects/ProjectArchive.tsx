import { Alert, Anchor, Button, Modal, Stack, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { Link } from "react-router-dom";

import {
    type Project,
    type ProjectReplacement,
    useArchiveProject,
    useProjectReplacement,
    useUnarchiveProject,
} from "../../shared/api/queries";
import { ARCHIVE_TONE } from "../../shared/theme/semanticColors";
import { formatArchivedAt } from "./archiveFormat";
import ProjectSearchSelect from "./ProjectSearchSelect";

type ProjectRef = NonNullable<ProjectReplacement["replaced_by"]>;

function ProjectLink({ project }: { project: ProjectRef }) {
    return (
        <Anchor component={Link} to={`/projects/${project.id}`} fw={600}>
            {project.name}
            {project.project_number ? ` (${project.project_number})` : ""}
        </Anchor>
    );
}

// Archivieren (docs/features/feature-project-archive.md): ein ersetztes oder
// überholtes Projekt verschwindet aus allen Listen und Summen, bleibt aber per
// URL erreichbar. Das UI-Wort ist „Archiviert", nie „Status" (Lebenszyklus).

/** Hinweis oben auf der Detailseite eines archivierten Projekts, mit dem
 * Nachfolger („Ersetzt durch …“); ein Nachfolger zeigt umgekehrt, welche
 * archivierten Projekte er ersetzt (feature-project-archive.md → „Ersetzt durch“). */
export function ArchiveBanner({ project }: { project: Project }) {
    const { data: replacement } = useProjectReplacement(project.id ?? Number.NaN);
    const replaces = replacement?.replaces ?? [];
    const backReference =
        replaces.length > 0 ? (
            <Alert color={ARCHIVE_TONE} variant="light" title="Nachfolgeprojekt">
                <Text size="sm">
                    Ersetzt{" "}
                    {replaces.map((old, index) => (
                        <span key={old.id}>
                            {index > 0 && ", "}
                            <ProjectLink project={old} />
                        </span>
                    ))}{" "}
                    (archiviert).
                </Text>
            </Alert>
        ) : null;
    if (!project.is_archived) return backReference;
    const date = formatArchivedAt(project.archived_at);
    return (
        <Alert color={ARCHIVE_TONE} variant="light" title={date ? `Archiviert am ${date}` : "Archiviert"}>
            <Stack gap={4}>
                {replacement?.replaced_by && (
                    <Text size="sm">
                        Ersetzt durch <ProjectLink project={replacement.replaced_by} />.
                    </Text>
                )}
                <Text size="sm">
                    Dieses Projekt wurde ersetzt oder ist überholt. Es erscheint in keiner Liste,
                    keiner Karte und zählt beim übergeordneten Projekt nicht mit.
                </Text>
                {project.archived_reason && (
                    <Text size="sm">
                        <strong>Begründung:</strong> {project.archived_reason}
                    </Text>
                )}
            </Stack>
        </Alert>
    );
}

type ArchiveModalProps = {
    project: Pick<Project, "id" | "name" | "is_archived">;
    opened: boolean;
    onClose: () => void;
};

/** Archivieren (Begründung Pflicht) bzw. Wiederherstellen (Begründung optional). */
export function ArchiveProjectModal({ project, opened, onClose }: ArchiveModalProps) {
    const archive = useArchiveProject();
    const unarchive = useUnarchiveProject();
    const [reason, setReason] = useState("");
    const [successorId, setSuccessorId] = useState<number | null>(null);
    const [error, setError] = useState<string | null>(null);
    const restoring = Boolean(project.is_archived);
    const pending = archive.isPending || unarchive.isPending;

    const close = () => {
        setReason("");
        setSuccessorId(null);
        setError(null);
        onClose();
    };

    const submit = async () => {
        if (project.id == null) return;
        setError(null);
        try {
            if (restoring) {
                await unarchive.mutateAsync({ projectId: project.id, reason: reason.trim() });
                notifications.show({
                    color: "green",
                    title: "Projekt wiederhergestellt",
                    message: `„${project.name}" zählt wieder in Listen und beim übergeordneten Projekt.`,
                });
            } else {
                await archive.mutateAsync({
                    projectId: project.id,
                    reason: reason.trim(),
                    replacedByProjectId: successorId,
                });
                notifications.show({
                    color: "green",
                    title: "Projekt archiviert",
                    message: `„${project.name}" ist archiviert.`,
                });
            }
            close();
        } catch (e) {
            // A refusal names the blocking links (FinVe, GVFG, Teilprojekte) in `detail`.
            const detail = (e as { details?: { detail?: unknown } } | undefined)?.details?.detail;
            setError(typeof detail === "string" ? detail : "Die Aktion ist fehlgeschlagen.");
        }
    };

    return (
        <Modal
            opened={opened}
            onClose={close}
            title={restoring ? "Projekt wiederherstellen" : "Projekt archivieren"}
            centered
        >
            <Stack gap="md">
                {restoring ? (
                    <Text size="sm">
                        „{project.name}" erscheint danach wieder in Listen, Karte und Picker und
                        zählt beim übergeordneten Projekt mit.
                    </Text>
                ) : (
                    <Text size="sm">
                        Für Projekte, die durch andere ersetzt wurden oder überholt sind. „{project.name}"
                        behält seine Historie, erscheint aber in keiner Liste und zählt beim
                        übergeordneten Projekt nicht mehr mit. Für Dubletten ist „Zusammenführen" da;
                        ein abgebrochenes Projekt bleibt sichtbar.
                    </Text>
                )}
                <Textarea
                    label="Begründung"
                    description={restoring ? "Optional, steht im Änderungsprotokoll." : "Was ersetzt das Projekt?"}
                    required={!restoring}
                    autosize
                    minRows={2}
                    value={reason}
                    onChange={(e) => setReason(e.currentTarget.value)}
                />
                {!restoring && (
                    <ProjectSearchSelect
                        label="Ersetzt durch (optional)"
                        description="Wenn genau ein Projekt dieses ersetzt: Beide Seiten verweisen dann aufeinander, und Importvorschläge gehen an den Nachfolger."
                        value={successorId}
                        onChange={setSuccessorId}
                    />
                )}
                {error && (
                    <Alert color="red" variant="light">
                        {error}
                    </Alert>
                )}
                <div className="idt-modal-footer">
                    <Button variant="default" onClick={close} disabled={pending}>
                        Abbrechen
                    </Button>
                    <Button
                        onClick={submit}
                        loading={pending}
                        disabled={!restoring && reason.trim() === ""}
                    >
                        {restoring ? "Wiederherstellen" : "Archivieren"}
                    </Button>
                </div>
            </Stack>
        </Modal>
    );
}
