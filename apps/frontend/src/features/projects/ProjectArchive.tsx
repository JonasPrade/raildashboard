import { Alert, Button, Modal, Stack, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";

import { type Project, useArchiveProject, useUnarchiveProject } from "../../shared/api/queries";
import { ARCHIVE_TONE } from "../../shared/theme/semanticColors";
import { formatArchivedAt } from "./archiveFormat";

// Archivieren (docs/features/feature-project-archive.md): ein ersetztes oder
// überholtes Projekt verschwindet aus allen Listen und Summen, bleibt aber per
// URL erreichbar. Das UI-Wort ist „Archiviert", nie „Status" (Lebenszyklus).

/** Hinweis oben auf der Detailseite eines archivierten Projekts. */
export function ArchiveBanner({ project }: { project: Project }) {
    if (!project.is_archived) return null;
    const date = formatArchivedAt(project.archived_at);
    return (
        <Alert color={ARCHIVE_TONE} variant="light" title={date ? `Archiviert am ${date}` : "Archiviert"}>
            <Stack gap={4}>
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
    const [error, setError] = useState<string | null>(null);
    const restoring = Boolean(project.is_archived);
    const pending = archive.isPending || unarchive.isPending;

    const close = () => {
        setReason("");
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
                await archive.mutateAsync({ projectId: project.id, reason: reason.trim() });
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
