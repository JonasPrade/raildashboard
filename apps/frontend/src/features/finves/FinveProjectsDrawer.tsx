import { useState } from "react";
import { Anchor, Badge, Button, Drawer, Group, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Link } from "react-router-dom";

import { type FinveListItem, useUpdateFinveProjects } from "../../shared/api/queries";
import { useIsMobile } from "../../shared/hooks/useBreakpoint";
import { openConfirmModal } from "../../shared/ui/confirmModal";
import ProjectSearchSelect from "../projects/ProjectSearchSelect";

type Props = {
    /** The FinVe being edited; null closes the drawer. */
    finve: FinveListItem | null;
    onClose: () => void;
};

/**
 * „Projekte bearbeiten“ for one FinVe: remove permanent project links and add
 * new ones. Each action is saved at once (logged per project, planning state
 * recomputed). Sammel-FinVe year links come from the Haushalt import and are
 * listed without a remove action; those of archived projects are marked.
 */
export default function FinveProjectsDrawer({ finve, onClose }: Props) {
    const isMobile = useIsMobile();
    const updateLinks = useUpdateFinveProjects();
    const [selected, setSelected] = useState<number | null>(null);

    const run = (change: { addProjectIds?: number[]; removeProjectIds?: number[] }, done: string) => {
        if (!finve) return;
        updateLinks.mutate(
            { finveId: finve.id, ...change },
            {
                onSuccess: () => notifications.show({ color: "green", title: "FinVe-Zuordnung geändert", message: done }),
                onError: (err) =>
                    notifications.show({
                        color: "red",
                        title: "Ändern fehlgeschlagen",
                        message: (err as Error)?.message ?? "Unbekannter Fehler",
                    }),
            },
        );
    };

    const remove = (project: { id: number; name: string }) =>
        openConfirmModal({
            title: "Zuordnung entfernen",
            children: (
                <Text size="sm" mb="md">
                    Soll das Projekt „{project.name}“ von FinVe {finve?.id} gelöst werden? Der Planungsstand des
                    Projekts wird neu berechnet; die Änderung steht in seinem Änderungsprotokoll und lässt sich
                    dort zurücksetzen.
                </Text>
            ),
            labels: { confirm: "Entfernen", cancel: "Abbrechen" },
            danger: true,
            onConfirm: () => run({ removeProjectIds: [project.id] }, `„${project.name}“ wurde gelöst.`),
        });

    const permanent = new Set(finve?.permanent_project_ids ?? []);

    return (
        <Drawer
            opened={finve != null}
            onClose={() => {
                setSelected(null);
                onClose();
            }}
            title={finve ? `Projekte der FinVe ${finve.id}` : ""}
            position="right"
            size={isMobile ? "100%" : "lg"}
            overlayProps={{ opacity: 0.4, blur: 4 }}
        >
            {finve && (
                <Stack gap="lg">
                    <Text size="sm" c="dimmed">
                        {finve.name ?? "—"}
                    </Text>

                    <Stack gap="xs">
                        <Text component="div" className="idt-eyebrow">
                            Zugeordnete Projekte
                        </Text>
                        {finve.projects.length === 0 && (
                            <Text size="sm" c="dimmed">Keine Projekte zugeordnet.</Text>
                        )}
                        {finve.projects.map((project) => (
                            <Group key={project.id} justify="space-between" wrap="nowrap" gap="sm">
                                <Group gap="xs" wrap="nowrap" style={{ minWidth: 0 }}>
                                    <Text size="xs" c="dimmed" className="idt-tnum">{project.id}</Text>
                                    <Anchor component={Link} to={`/projects/${project.id}`} size="sm" truncate>
                                        {project.name}
                                    </Anchor>
                                </Group>
                                {permanent.has(project.id) ? (
                                    <Button
                                        size="xs"
                                        variant="default"
                                        onClick={() => remove(project)}
                                        disabled={updateLinks.isPending}
                                    >
                                        Entfernen
                                    </Button>
                                ) : project.is_archived ? (
                                    <Badge
                                        variant="outline"
                                        color="gray"
                                        title="Archiviertes Projekt: die Zuordnung bleibt als Historie, zählt aber nicht mehr mit"
                                    >
                                        Archiviert
                                    </Badge>
                                ) : (
                                    <Badge variant="outline" title="Jahresbezogene Zuordnung aus dem Haushaltsimport">
                                        Haushaltsjahr
                                    </Badge>
                                )}
                            </Group>
                        ))}
                    </Stack>

                    <Group align="flex-end" gap="sm" wrap="wrap">
                        <div style={{ flex: "1 1 240px" }}>
                            <ProjectSearchSelect label="Projekt hinzufügen" value={selected} onChange={setSelected} />
                        </div>
                        <Button
                            disabled={selected == null}
                            loading={updateLinks.isPending}
                            onClick={() => {
                                if (selected == null) return;
                                run({ addProjectIds: [selected] }, "Das Projekt wurde zugeordnet.");
                                setSelected(null);
                            }}
                        >
                            Hinzufügen
                        </Button>
                    </Group>
                </Stack>
            )}
        </Drawer>
    );
}
