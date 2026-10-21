import {
    Alert,
    Badge,
    Button,
    Container,
    Group,
    Modal,
    Paper,
    Stack,
    Text,
    Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../../../lib/auth";
import RequirePermission from "../../../components/RequirePermission";
import {
    useDeleteProject,
    useDraftProjects,
    useFinalizeProject,
    type Project,
} from "../../../shared/api/queries";
import { LoadingState } from "../../../shared/ui/LoadingState";

function DraftsPageContent() {
    const { can } = useAuth();
    const canManage = can("project.create");
    const navigate = useNavigate();

    const { data: drafts, isLoading } = useDraftProjects(canManage);
    const finalize = useFinalizeProject();
    const del = useDeleteProject();

    const [toDelete, setToDelete] = useState<Project | null>(null);

    const handleFinalize = async (p: Project) => {
        if (p.id == null) return;
        try {
            await finalize.mutateAsync(p.id);
            notifications.show({
                color: "green",
                title: "Projekt fertiggestellt",
                message: `„${p.name}" ist jetzt veröffentlicht.`,
            });
        } catch {
            notifications.show({ color: "red", title: "Fehler", message: "Fertigstellen fehlgeschlagen." });
        }
    };

    const handleDelete = async () => {
        if (toDelete?.id == null) return;
        try {
            await del.mutateAsync(toDelete.id);
            notifications.show({ color: "green", title: "Entwurf verworfen", message: `„${toDelete.name}" wurde gelöscht.` });
            setToDelete(null);
        } catch {
            notifications.show({ color: "red", title: "Fehler", message: "Verwerfen fehlgeschlagen." });
        }
    };

    return (
        <Container size="lg" py="xl">
            <Stack gap="lg">
                <Group justify="space-between" align="center">
                    <Title order={1}>Projekt-Entwürfe</Title>
                    <Button component={Link} to="/admin/projects/new" variant="light">
                        Neues Projekt
                    </Button>
                </Group>

                <Text c="dimmed" size="sm">
                    Noch nicht finalisierte Projekte. Entwürfe sind nicht öffentlich sichtbar.
                    Bearbeite sie weiter und stelle sie fertig oder verwirf sie.
                </Text>

                {isLoading ? (
                    <LoadingState rows={6} />
                ) : !drafts || drafts.length === 0 ? (
                    <Alert color="gray" variant="light">Keine Entwürfe vorhanden.</Alert>
                ) : (
                    <Stack gap="sm">
                        {drafts.map((p) => (
                            <Paper withBorder p="var(--card-pad)" key={p.id}>
                                <Group justify="space-between" align="center" wrap="nowrap">
                                    <Stack gap={2} style={{ minWidth: 0 }}>
                                        <Group gap={8} align="center">
                                            <Text fw={600} truncate>{p.name}</Text>
                                            {p.project_number && (
                                                <Badge variant="light" size="sm">{p.project_number}</Badge>
                                            )}
                                            {p.geojson_representation
                                                ? <Badge color="teal" variant="light" size="sm">Geometrie</Badge>
                                                : <Badge color="gray" variant="light" size="sm">ohne Geometrie</Badge>}
                                        </Group>
                                        {p.description && (
                                            <Text size="sm" c="dimmed" lineClamp={1}>{p.description}</Text>
                                        )}
                                    </Stack>
                                    <Group gap="xs" wrap="nowrap">
                                        <Button
                                            size="xs"
                                            variant="default"
                                            onClick={() => navigate(`/admin/projects/new/${p.id}`)}
                                        >
                                            Weiter bearbeiten
                                        </Button>
                                        <Button
                                            size="xs"
                                            loading={finalize.isPending}
                                            onClick={() => handleFinalize(p)}
                                        >
                                            Fertigstellen
                                        </Button>
                                        <Button
                                            size="xs"
                                            color="red"
                                            variant="subtle"
                                            onClick={() => setToDelete(p)}
                                        >
                                            Verwerfen
                                        </Button>
                                    </Group>
                                </Group>
                            </Paper>
                        ))}
                    </Stack>
                )}
            </Stack>

            <Modal opened={toDelete != null} onClose={() => setToDelete(null)} title="Entwurf verwerfen" centered>
                <Stack gap="md">
                    <Text size="sm">
                        Soll der Entwurf „{toDelete?.name}" endgültig gelöscht werden? Diese Aktion
                        kann nicht rückgängig gemacht werden.
                    </Text>
                    <div className="idt-modal-footer">
                        <Button variant="default" onClick={() => setToDelete(null)} disabled={del.isPending}>
                            Abbrechen
                        </Button>
                        <Button color="red" variant="filled" onClick={handleDelete} loading={del.isPending}>
                            Verwerfen
                        </Button>
                    </div>
                </Stack>
            </Modal>
        </Container>
    );
}

export default function DraftsPage() {
    return (
        <RequirePermission perm="project.create">
            <DraftsPageContent />
        </RequirePermission>
    );
}
