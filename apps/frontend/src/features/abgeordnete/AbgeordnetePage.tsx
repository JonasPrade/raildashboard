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
    Group,
    Loader,
    Select,
    Stack,
    Table,
    Text,
    TextInput,
} from "@mantine/core";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import { IconSearch } from "@tabler/icons-react";
import { Link, useSearchParams } from "react-router-dom";

import { ChronicleCard, ChronicleDataChip, ChronicleHeadline } from "../../components/chronicle";
import {
    type PoliticianListItem,
    usePoliticians,
    useParliamentStatus,
    usePolitician,
} from "../../shared/api/queries";
import { COMMITTEE_LABELS, CommitteeBadges, formatWeight } from "./mandateDisplay";

const COMMITTEE_OPTIONS = [
    { value: "verkehr", label: "Verkehrsausschuss" },
    { value: "haushalt", label: "Haushaltsausschuss" },
];

function PoliticianProjects({ mandateId }: { mandateId: number }) {
    const { data, isLoading } = usePolitician(mandateId);

    if (isLoading) return <Loader size="sm" />;
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
                    <Table.Th ta="right">Im Wahlkreis</Table.Th>
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
                        <Table.Td ta="right">
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
                                color={politician.is_direct_mandate ? "preussen" : "gray"}
                            >
                                {politician.is_direct_mandate
                                    ? "Direktmandat"
                                    : "über Liste, hier angetreten"}
                            </Badge>
                        </Group>
                    </Stack>
                    <Group gap="xs" wrap="nowrap">
                        <CommitteeBadges committees={politician.committees} />
                        <ChronicleDataChip>
                            {politician.project_count}{" "}
                            {politician.project_count === 1 ? "Projekt" : "Projekte"}
                        </ChronicleDataChip>
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
                <ChronicleHeadline as="h1">Abgeordnete</ChronicleHeadline>
                <Text c="dimmed">
                    Wer ist für welches Projekt zuständig? Namen suchen, auf Verkehrs- oder
                    Haushaltsausschuss filtern und die Projekte im jeweiligen Wahlkreis lesen.
                </Text>
            </Stack>

            {status.data && !status.data.period && (
                <Alert color="gray" variant="light">
                    Es sind noch keine Abgeordnetendaten importiert. Ein Import lässt sich im
                    Adminbereich anstoßen (Recht „Abgeordnetenstand aktualisieren“).
                </Alert>
            )}

            {status.data?.is_stale && status.data.period && (
                <Alert color="gold" variant="light">
                    Der Abgeordnetenstand ist älter als {status.data.stale_after_days} Tage
                    {importedAt
                        ? ` (zuletzt am ${new Date(importedAt).toLocaleDateString("de-DE", {
                              timeZone: "Europe/Berlin",
                          })})`
                        : ""}
                    . Nachrücker und Ausschussumbesetzungen können die Zuordnung verschoben haben.
                </Alert>
            )}

            <ChronicleCard>
                <Group align="flex-end" gap="md" wrap="wrap">
                    <TextInput
                        label="Name"
                        placeholder="Namensteil eingeben"
                        leftSection={<IconSearch size={16} />}
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
            </ChronicleCard>

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
                <Group justify="center" py="xl">
                    <Loader />
                </Group>
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
