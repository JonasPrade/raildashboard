import { Alert, Badge, Button, Container, Group, Paper, Stack, Text, Title } from "@mantine/core";
import { useState } from "react";
import { Link } from "react-router-dom";

import RequirePermission from "../../../components/RequirePermission";
import { type ArchivedProject, useArchivedProjects } from "../../../shared/api/queries";
import { LoadingState } from "../../../shared/ui/LoadingState";
import { ArchiveProjectModal } from "../../projects/ProjectArchive";
import { formatArchivedAt } from "../../projects/archiveFormat";

// Archiv (docs/features/feature-project-archive.md): ersetzte und überholte
// Projekte, die nirgends mehr zählen. Karten statt Tabelle, damit die Seite bei
// 360 px ohne Querscrollen lesbar bleibt.

function ArchivePageContent() {
    const { data: archived, isLoading } = useArchivedProjects();
    const [toRestore, setToRestore] = useState<ArchivedProject | null>(null);

    return (
        <Container size="lg" py="xl">
            <Stack gap="lg">
                <Title order={1}>Archiv</Title>
                <Text c="dimmed" size="sm">
                    Archivierte Projekte wurden durch andere ersetzt oder sind überholt. Sie behalten
                    ihre Historie, erscheinen aber in keiner Liste und zählen beim übergeordneten
                    Projekt nicht mit. Wiederherstellen nimmt sie wieder auf.
                </Text>

                {isLoading ? (
                    <LoadingState rows={6} />
                ) : !archived || archived.length === 0 ? (
                    <Alert color="gray" variant="light">Keine archivierten Projekte.</Alert>
                ) : (
                    <Stack gap="sm">
                        {archived.map((p) => {
                            const date = formatArchivedAt(p.archived_at);
                            return (
                                <Paper withBorder p="var(--card-pad)" key={p.id}>
                                    <Group justify="space-between" align="flex-start" wrap="wrap" gap="sm">
                                        <Stack gap={4} style={{ flex: "1 1 240px", minWidth: 0 }}>
                                            <Group gap={8} align="center" wrap="wrap">
                                                <Text
                                                    fw={600}
                                                    component={Link}
                                                    to={`/projects/${p.id}`}
                                                    style={{ overflowWrap: "anywhere" }}
                                                >
                                                    {p.name}
                                                </Text>
                                                {p.project_number && (
                                                    <Badge variant="light" size="sm">{p.project_number}</Badge>
                                                )}
                                            </Group>
                                            {p.archived_reason && (
                                                <Text size="sm" style={{ overflowWrap: "anywhere" }}>
                                                    {p.archived_reason}
                                                </Text>
                                            )}
                                            <Text size="xs" c="dimmed">
                                                {date ? `Archiviert am ${date}` : "Archiviert"}
                                                {p.superior_project_id != null && (
                                                    <>
                                                        {" · Teil von "}
                                                        <Link to={`/projects/${p.superior_project_id}`}>
                                                            {p.superior_project_name ?? `Projekt ${p.superior_project_id}`}
                                                        </Link>
                                                    </>
                                                )}
                                            </Text>
                                        </Stack>
                                        <Button size="xs" variant="default" onClick={() => setToRestore(p)}>
                                            Wiederherstellen
                                        </Button>
                                    </Group>
                                </Paper>
                            );
                        })}
                    </Stack>
                )}
            </Stack>

            {toRestore && (
                <ArchiveProjectModal
                    project={{ id: toRestore.id, name: toRestore.name, is_archived: true }}
                    opened
                    onClose={() => setToRestore(null)}
                />
            )}
        </Container>
    );
}

export default function ArchivePage() {
    return (
        <RequirePermission perm="project.delete">
            <ArchivePageContent />
        </RequirePermission>
    );
}
