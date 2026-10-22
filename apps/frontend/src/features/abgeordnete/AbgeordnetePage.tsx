/**
 * The working list before an appointment: type a name, set the committee
 * filter, read the projects in that constituency.
 *
 * In the prototype this was the third entry point that got added and the one
 * that ended up being used most — before a meeting you have the person, not
 * their constituency.
 */
import { useMemo, useState } from "react";
import {
    Accordion,
    Alert,
    Anchor,
    Badge,
    Container,
    Group,
    Paper,
    Select,
    Stack,
    Table,
    Text,
    TextInput,
    Title,
} from "@mantine/core";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import { Search } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

import { useAuth } from "../../lib/auth";
import {
    type PoliticianListItem,
    usePoliticians,
    useParliamentStatus,
    usePolitician,
} from "../../shared/api/queries";
import { COMMITTEE_LABELS, CommitteeBadges, formatWeight } from "./mandateDisplay";
import { LoadingState } from "../../shared/ui/LoadingState";

const COMMITTEE_OPTIONS = [
    { value: "verkehr", label: "Verkehrsausschuss" },
    { value: "haushalt", label: "Haushaltsausschuss" },
];

function PoliticianProjects({ mandateId }: { mandateId: number }) {
    const { data, isLoading } = usePolitician(mandateId);

    if (isLoading) return <LoadingState rows={3} />;
    if (!data) return <Text c="dimmed">Konnte nicht geladen werden.</Text>;

    if (data.projects.length === 0) {
        return (
            <Text size="sm" c="dimmed">
                {data.constituency
                    ? "Keine Projekte mit Geometrie in diesem Wahlkreis."
                    : "Kein Wahlkreisbezug — über die Landesliste ohne eigene Kandidatur."}
            </Text>
        );
    }

    return (
        <ResponsiveTable minWidth={640} highlightOnHover>
            <Table.Thead>
                <Table.Tr>
                    <Table.Th>Projekt</Table.Th>
                    <Table.Th>Nummer</Table.Th>
                    <Table.Th className="num">Im Wahlkreis</Table.Th>
                </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
                {data.projects.map((project) => (
                    <Table.Tr key={project.project_id}>
                        <Table.Td>
                            <Anchor component={Link} to={`/projects/${project.project_id}`}>
                                {project.name}
                            </Anchor>
                        </Table.Td>
                        <Table.Td>
                            <Text size="sm" c="dimmed">
                                {project.project_number ?? "—"}
                            </Text>
                        </Table.Td>
                        <Table.Td className="num">
                            {formatWeight(project.length_km, project.overlap_kind)}
                        </Table.Td>
                    </Table.Tr>
                ))}
            </Table.Tbody>
        </ResponsiveTable>
    );
}

function PoliticianRow({ politician }: { politician: PoliticianListItem }) {
    return (
        <Accordion.Item value={String(politician.mandate_id)}>
            <Accordion.Control>
                <Group justify="space-between" wrap="nowrap" pr="sm">
                    <Stack gap={2}>
                        <Group gap="xs">
                            <Text fw={600}>{politician.name}</Text>
                            {politician.fraction && (
                                <Text size="sm" c="dimmed">
                                    {politician.fraction}
                                </Text>
                            )}
                        </Group>
                        <Group gap="xs">
                            <Text size="xs" c="dimmed">
                                {politician.constituency
                                    ? `${politician.constituency.number} · ${politician.constituency.name}`
                                    : "ohne Wahlkreisbezug"}
                            </Text>
                            <Badge
                                size="xs"
                                variant={politician.is_direct_mandate ? "filled" : "outline"}
                                color={politician.is_direct_mandate ? "violet" : "gray"}
                            >
                                {politician.is_direct_mandate
                                    ? "Direktmandat"
                                    : "über Liste, hier angetreten"}
                            </Badge>
                        </Group>
                    </Stack>
                    <Group gap="xs" wrap="nowrap">
                        <CommitteeBadges committees={politician.committees} />
                        <Badge variant="outline">
                            {politician.project_count}{" "}
                            {politician.project_count === 1 ? "Projekt" : "Projekte"}
                        </Badge>
                    </Group>
                </Group>
            </Accordion.Control>
            <Accordion.Panel>
                <Stack gap="sm">
                    <PoliticianProjects mandateId={politician.mandate_id} />
                    {politician.profile_url && (
                        <Anchor
                            href={politician.profile_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            size="sm"
                        >
                            Profil bei abgeordnetenwatch.de
                        </Anchor>
                    )}
                </Stack>
            </Accordion.Panel>
        </Accordion.Item>
    );
}

export default function AbgeordnetePage() {
    const { user } = useAuth();

    // The members of parliament are only shown to signed-in users; the API
    // answers 401 otherwise.
    if (user === null) {
        return (
            <Container size="md" py="xl">
                <Alert color="gray">Abgeordnete sind nur für angemeldete Nutzer sichtbar.</Alert>
            </Container>
        );
    }

    return <PoliticianWorkingList />;
}

function PoliticianWorkingList() {
    const [searchParams, setSearchParams] = useSearchParams();
    const [open, setOpen] = useState<string | null>(null);

    const query = searchParams.get("q") ?? "";
    const committee = searchParams.get("committee");
    const fraction = searchParams.get("fraction");

    const setParam = (key: string, value: string | null) => {
        const next = new URLSearchParams(searchParams);
        if (value) next.set(key, value);
        else next.delete(key);
        setSearchParams(next, { replace: true });
    };

    const status = useParliamentStatus();
    const { data, isLoading } = usePoliticians({ query, committee, fraction });

    const fractionOptions = useMemo(
        () => (status.data?.fractions ?? []).map((value) => ({ value, label: value })),
        [status.data],
    );

    const importedAt = status.data?.last_politician_import?.finished_at;

    return (
        <Stack gap="lg" p={{ base: "xs", sm: "xl" }} maw={1100} mx="auto">
            <Stack gap="xs">
                <Title order={1}>Abgeordnete</Title>
                <Text c="dimmed">
                    Wer ist für welches Projekt zuständig? Namen suchen, auf Verkehrs- oder
                    Haushaltsausschuss filtern und die Projekte im jeweiligen Wahlkreis lesen.
                </Text>
            </Stack>

            {status.data && !status.data.period && (
                <Alert color="gray" variant="light">
                    Es sind noch keine Abgeordnetendaten importiert. Ein Import lässt sich unter{" "}
                    <Anchor component={Link} to="/admin/abgeordnete">
                        Admin → Abgeordnetenstand
                    </Anchor>{" "}
                    anstoßen (Recht „Abgeordnetenstand aktualisieren“).
                </Alert>
            )}

            {status.data?.is_stale && status.data.period && (
                <Alert color="teal" variant="light">
                    Der Abgeordnetenstand ist älter als {status.data.stale_after_days} Tage
                    {importedAt
                        ? ` (zuletzt am ${new Date(importedAt).toLocaleDateString("de-DE", {
                              timeZone: "Europe/Berlin",
                          })})`
                        : ""}
                    . Nachrücker und Ausschussumbesetzungen können die Zuordnung verschoben haben.
                </Alert>
            )}

            <Paper withBorder p="var(--card-pad)">
                <Group align="flex-end" gap="md" wrap="wrap">
                    <TextInput
                        label="Name"
                        placeholder="Namensteil eingeben"
                        leftSection={<Search size={16} />}
                        value={query}
                        onChange={(event) => setParam("q", event.currentTarget.value || null)}
                        style={{ flex: "1 1 240px" }}
                    />
                    <Select
                        label="Ausschuss"
                        placeholder="alle"
                        clearable
                        data={COMMITTEE_OPTIONS}
                        value={committee}
                        onChange={(value) => setParam("committee", value)}
                        style={{ flex: "0 1 220px" }}
                    />
                    <Select
                        label="Fraktion"
                        placeholder="alle"
                        clearable
                        searchable
                        data={fractionOptions}
                        value={fraction}
                        onChange={(value) => setParam("fraction", value)}
                        style={{ flex: "0 1 260px" }}
                    />
                </Group>
            </Paper>

            <Group justify="space-between" align="baseline" wrap="wrap" gap="xs">
                <Text size="sm" c="dimmed">
                    {isLoading ? "lädt …" : `${data?.length ?? 0} Abgeordnete`}
                    {committee ? ` im ${COMMITTEE_LABELS[committee] ?? committee}` : ""}
                </Text>
                {status.data?.period && (
                    <Text size="xs" c="dimmed">
                        {status.data.period.label}
                        {importedAt
                            ? ` · Stand ${new Date(importedAt).toLocaleDateString("de-DE", {
                                  timeZone: "Europe/Berlin",
                              })}`
                            : ""}
                    </Text>
                )}
            </Group>

            {isLoading ? (
                <LoadingState rows={6} />
            ) : (data?.length ?? 0) === 0 ? (
                <Text c="dimmed">Keine Abgeordneten gefunden.</Text>
            ) : (
                <Accordion value={open} onChange={setOpen} variant="separated">
                    {data?.map((politician) => (
                        <PoliticianRow key={politician.mandate_id} politician={politician} />
                    ))}
                </Accordion>
            )}

            <Text size="xs" c="dimmed">
                Personendaten: abgeordnetenwatch.de, API v2 (CC0). „Über Liste, hier angetreten“
                meint die Wahlkreiskandidatur, keinen gepflegten Betreuungswahlkreis — den kennt
                die Quelle nicht.
            </Text>
        </Stack>
    );
}
