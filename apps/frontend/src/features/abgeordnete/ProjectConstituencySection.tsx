/**
 * "Wahlkreise und Abgeordnete" on the project detail page.
 *
 * Answers the one question a conversation starts with: what connects this member
 * of parliament with this project? Constituencies come heaviest first, because
 * 51 km and 3 km are not the same argument.
 */
import { useState } from "react";
import {
    Alert,
    Anchor,
    Badge,
    Divider,
    Group,
    Paper,
    Stack,
    Text,
    Title,
} from "@mantine/core";
import { Link } from "react-router-dom";

import { useAuth } from "../../lib/auth";
import { type ProjectConstituency, useProjectConstituencies } from "../../shared/api/queries";
import { MandateGroup, formatShare, formatWeight } from "./mandateDisplay";
import { LoadingState } from "../../shared/ui/LoadingState";

function ConstituencyBlock({ constituency }: { constituency: ProjectConstituency }) {
    return (
        <Stack gap="sm">
            <Group justify="space-between" align="flex-start" wrap="nowrap">
                <Stack gap={2}>
                    <Text fw={700}>
                        {constituency.number} · {constituency.name}
                    </Text>
                    {constituency.state && (
                        <Text size="xs" c="dimmed">
                            {constituency.state}
                        </Text>
                    )}
                </Stack>
                <Group gap="xs">
                    <Badge variant="outline">
                        {formatWeight(constituency.length_km, constituency.overlap_kind)}
                    </Badge>
                    {constituency.overlap_kind !== "point" && (
                        <Badge variant="outline">
                            {formatShare(constituency.share)} des Projekts
                        </Badge>
                    )}
                </Group>
            </Group>

            {constituency.has_any_mandate ? (
                <Stack gap="md">
                    <MandateGroup
                        title="Direktmandat"
                        mandates={constituency.direct_mandates}
                        emptyText="Kein Direktmandat besetzt"
                    />
                    <MandateGroup
                        title="Über Liste, hier angetreten"
                        hint="keine Betreuung, sondern die Wahlkreiskandidatur"
                        mandates={constituency.list_mandates}
                        emptyText="Niemand über die Liste angetreten"
                    />
                </Stack>
            ) : (
                <Text size="sm" c="dimmed">
                    Kein Direktmandat besetzt, und niemand ist hier über die Liste angetreten —
                    in diesem Wahlkreis gibt es keinen naheliegenden Ansprechpartner.
                </Text>
            )}
        </Stack>
    );
}

export default function ProjectConstituencySection({ projectId }: { projectId: number }) {
    const { can } = useAuth();
    const { data, isLoading, isError } = useProjectConstituencies(projectId);
    const [expanded, setExpanded] = useState(false);

    if (isLoading) {
        return (
            <Paper withBorder p="var(--card-pad)">
                <LoadingState rows={3} />
            </Paper>
        );
    }
    if (isError || !data) {
        return (
            <Paper withBorder p="var(--card-pad)">
                <Text c="dimmed">Wahlkreiszuordnung konnte nicht geladen werden.</Text>
            </Paper>
        );
    }

    const visible = expanded ? data.constituencies : data.constituencies.slice(0, 5);
    const hidden = data.constituencies.length - visible.length;
    const canEdit = can("project.edit");

    return (
        <Paper withBorder p="var(--card-pad)">
            <Stack gap="md">
                <Group justify="space-between" align="baseline">
                    <Title order={2}>Wahlkreise und Abgeordnete</Title>
                    {data.last_import?.finished_at && (
                        <Text size="xs" c="dimmed">
                            Abgeordnetenstand:{" "}
                            {new Date(data.last_import.finished_at).toLocaleDateString("de-DE", {
                                timeZone: "Europe/Berlin",
                            })}
                        </Text>
                    )}
                </Group>

                {!data.has_geometry && (
                    <Alert color="gray" variant="light">
                        Für dieses Projekt ist keine Geometrie hinterlegt — eine
                        Wahlkreiszuordnung ist deshalb nicht möglich.
                        {canEdit && " Die Geometrie lässt sich über „Geometrie verwalten“ ergänzen."}
                    </Alert>
                )}

                {data.has_geometry && data.constituencies.length === 0 && (
                    <Text c="dimmed">
                        Keine Wahlkreiszuordnung vorhanden. Entweder sind die
                        Wahlkreisgeometrien noch nicht importiert, oder die Projektgeometrie
                        liegt außerhalb der Wahlkreise.
                    </Text>
                )}

                {visible.map((constituency, index) => (
                    <Stack key={constituency.id} gap="sm">
                        {index > 0 && <Divider />}
                        <ConstituencyBlock constituency={constituency} />
                    </Stack>
                ))}

                {hidden > 0 && (
                    <Anchor component="button" type="button" onClick={() => setExpanded(true)}>
                        {hidden} weitere Wahlkreise anzeigen
                    </Anchor>
                )}

                {data.constituencies.length > 0 && (
                    <Text size="xs" c="dimmed">
                        Arbeitsliste nach Personen:{" "}
                        <Anchor component={Link} to="/abgeordnete">
                            Abgeordnete
                        </Anchor>
                    </Text>
                )}
            </Stack>
        </Paper>
    );
}
