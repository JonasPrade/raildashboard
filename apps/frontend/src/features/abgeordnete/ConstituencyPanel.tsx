/**
 * Selection panel for the constituency map layer: which projects lie in this
 * constituency, and who is responsible for them.
 */
import { Anchor, Badge, CloseButton, Group, ScrollArea, Stack, Text } from "@mantine/core";
import { Link } from "react-router-dom";

import { useIsMobile } from "../../shared/hooks/useBreakpoint";
import { useConstituency } from "../../shared/api/queries";
import { MandateGroup, formatWeight } from "./mandateDisplay";
import { LoadingState } from "../../shared/ui/LoadingState";
import ProjectHoverCard from "../projects/ProjectHoverCard";

export default function ConstituencyPanel({
    constituencyId,
    onClose,
}: {
    constituencyId: number;
    onClose: () => void;
}) {
    const { data, isLoading } = useConstituency(constituencyId);
    // On a phone the panel is a bottom sheet across the full width — a 340px
    // box pinned to the top-left would cover the constituency it describes.
    const isMobile = useIsMobile();

    return (
        <div
            style={{
                position: "absolute",
                ...(isMobile
                    ? { left: 0, right: 0, bottom: 0, maxHeight: "60%" }
                    : { top: 12, left: 12, width: 340, maxHeight: "calc(100% - 24px)" }),
                zIndex: 10,
                overflowY: "auto",
                background: "var(--surface)",
                color: "var(--text-body)",
                border: "2px solid var(--border-frame)",
                borderRadius: 0,
                padding: 12,
            }}
        >
            {isLoading || !data ? (
                <LoadingState rows={4} />
            ) : (
                <Stack gap="sm">
                    <Group justify="space-between" align="flex-start" wrap="nowrap">
                        <Stack gap={0}>
                            <Text fw={700}>
                                {data.number} · {data.name}
                            </Text>
                            {data.state && (
                                <Text size="xs" c="dimmed">
                                    {data.state}
                                </Text>
                            )}
                        </Stack>
                        <CloseButton onClick={onClose} aria-label="Wahlkreis schließen" />
                    </Group>

                    <ScrollArea.Autosize mah={isMobile ? 260 : 420}>
                        <Stack gap="md" pr="xs">
                            <Stack gap={4}>
                                <Group gap="xs" align="baseline">
                                    <Text component="div" className="idt-eyebrow">
                                        Projekte
                                    </Text>
                                    <Badge variant="outline">{data.projects.length}</Badge>
                                </Group>
                                {data.projects.length === 0 ? (
                                    <Text size="sm" c="dimmed" fs="italic">
                                        Keine Projekte mit Geometrie in diesem Wahlkreis.
                                    </Text>
                                ) : (
                                    data.projects.map((project) => (
                                        <Group
                                            key={project.project_id}
                                            justify="space-between"
                                            wrap="nowrap"
                                            gap="xs"
                                        >
                                            <ProjectHoverCard projectId={project.project_id}>
                                                <Anchor
                                                    component={Link}
                                                    to={`/projects/${project.project_id}`}
                                                    size="sm"
                                                >
                                                    {project.name}
                                                </Anchor>
                                            </ProjectHoverCard>
                                            <Text size="xs" c="dimmed" style={{ whiteSpace: "nowrap" }}>
                                                {formatWeight(project.length_km, project.overlap_kind)}
                                            </Text>
                                        </Group>
                                    ))
                                )}
                            </Stack>

                            {data.has_any_mandate ? (
                                <>
                                    <MandateGroup
                                        title="Direktmandat"
                                        mandates={data.direct_mandates}
                                        emptyText="Kein Direktmandat besetzt"
                                    />
                                    <MandateGroup
                                        title="Über Liste, hier angetreten"
                                        mandates={data.list_mandates}
                                        emptyText="Niemand über die Liste angetreten"
                                    />
                                </>
                            ) : (
                                <Text size="sm" c="dimmed">
                                    Kein Direktmandat besetzt, und niemand ist hier über die Liste
                                    angetreten — kein naheliegender Ansprechpartner.
                                </Text>
                            )}
                        </Stack>
                    </ScrollArea.Autosize>
                </Stack>
            )}
        </div>
    );
}
