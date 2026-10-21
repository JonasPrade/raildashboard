import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
    Alert,
    Anchor,
    Badge,
    Button,
    Container,
    Group,
    List,
    MultiSelect,
    Pagination,
    SegmentedControl,
    Select,
    Stack,
    Table,
    Text,
    TextInput,
} from "@mantine/core";
import { modals } from "@mantine/modals";
import { notifications } from "@mantine/notifications";
import { ChronicleCard, ChronicleHeadline } from "../../components/chronicle";
import RequirePermission from "../../components/RequirePermission";
import { filterProjectOption } from "../../lib/filterProjectOption";
import { Plus } from "lucide-react";
import CreateDraftProjectModal from "../projects/CreateDraftProjectModal";
import {
    useConfirmGvfgImport,
    useGvfgParseResult,
    useProjectOptions,
    type GvfgParseResultJson,
    type GvfgParsedEntry,
} from "../../shared/api/queries";
import { formatNumberDe } from "../../shared/format";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import { LoadingState } from "../../shared/ui/LoadingState";

const PAGE_SIZE = 50;

const SOURCE_LABEL: Record<string, string> = {
    previous: "wie Vorausgabe",
    key: "Schlüssel",
    key_without_suffix: "Schlüssel ohne Suffix",
    none: "",
};

function aidTotal(entry: GvfgParsedEntry): number | null {
    const total = entry.amounts.find((a) => a.category === "SUM");
    return total?.aid_total != null ? Number(total.aid_total) : null;
}

function GvfgReviewPageContent() {
    const { parseResultId } = useParams<{ parseResultId: string }>();
    const id = Number(parseResultId);
    const navigate = useNavigate();
    const { data: record, isLoading, isError } = useGvfgParseResult(id);
    const { data: projectOptions } = useProjectOptions();
    const confirm = useConfirmGvfgImport();

    const result = (record?.result_json ?? null) as GvfgParseResultJson | null;
    const [assignments, setAssignments] = useState<Record<string, number[]> | null>(null);
    const [create, setCreate] = useState<Set<string>>(new Set());
    const [view, setView] = useState<"review" | "all">("review");
    const [land, setLand] = useState<string | null>(null);
    const [search, setSearch] = useState("");
    const [page, setPage] = useState(1);
    // Entry whose "project not found" dialog is open (one page-level modal).
    const [draftFor, setDraftFor] = useState<GvfgParsedEntry | null>(null);

    const initial = useMemo(() => {
        const out: Record<string, number[]> = {};
        for (const entry of result?.entries ?? []) {
            out[entry.key] = result?.suggestions.by_key[entry.key]?.selected ?? [];
        }
        return out;
    }, [result]);
    const current = assignments ?? initial;

    const options = useMemo(
        () =>
            (projectOptions ?? []).map((p) => ({
                value: String(p.id),
                label: `${p.project_number ?? "–"} – ${p.name}`,
            })),
        [projectOptions],
    );

    if (isLoading) return <Container py="xl"><LoadingState rows={6} /></Container>;
    if (isError || !record || !result) {
        return (
            <Container size="sm" py="xl">
                <Alert color="red" variant="light" title="Fehler">Import-Lauf konnte nicht geladen werden.</Alert>
            </Container>
        );
    }

    const confirmed = record.confirmed_at !== null;
    const needsReview = (entry: GvfgParsedEntry) => {
        const suggestion = result.suggestions.by_key[entry.key];
        return (suggestion?.flags.length ?? 0) > 0 || (current[entry.key] ?? []).length === 0;
    };
    const lands = [...new Set(result.entries.map((e) => e.land))].sort();
    const needle = search.trim().toLowerCase();
    const rows = result.entries.filter(
        (e) =>
            (view === "all" || needsReview(e)) &&
            (!land || e.land === land) &&
            (!needle || e.key.toLowerCase().includes(needle) || (e.name ?? "").toLowerCase().includes(needle)),
    );
    const pageRows = rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
    const withoutProject = result.entries.filter((e) => (current[e.key] ?? []).length === 0);

    const setProjects = (key: string, ids: number[]) => setAssignments({ ...current, [key]: ids });
    const toggleCreate = (key: string, on: boolean) => {
        const next = new Set(create);
        if (on) next.add(key);
        else next.delete(key);
        setCreate(next);
    };

    const handleConfirm = () =>
        modals.openConfirmModal({
            title: `${result.title ?? "GVFG-Programm"} übernehmen?`,
            children: (
                <Text size="sm">
                    {result.entries.length} Vorhaben ({record.is_annex ? "Anhang" : "Hauptteil"}) ersetzen die
                    entsprechenden Einträge dieser Ausgabe. {create.size} Projekte werden neu angelegt (als Entwurf, bis sie gepflegt und fertiggestellt sind),{" "}
                    {withoutProject.filter((e) => !create.has(e.key)).length} Vorhaben bleiben ohne Projekt.
                </Text>
            ),
            labels: { confirm: "Übernehmen", cancel: "Abbrechen" },
            onConfirm: async () => {
                try {
                    const stats = await confirm.mutateAsync({
                        id,
                        body: {
                            assignments: Object.fromEntries(
                                Object.entries(current).filter(([key]) => !create.has(key)),
                            ),
                            create_projects: [...create],
                        },
                    });
                    notifications.show({
                        color: "green",
                        title: "GVFG-Programm übernommen",
                        message: `${stats.entries} Vorhaben, ${stats.links} Zuordnungen, ${stats.projects_created} neue Projekte.`,
                    });
                    navigate("/admin/gvfg-import");
                } catch (error) {
                    notifications.show({
                        color: "red",
                        title: "Übernahme fehlgeschlagen",
                        message: error instanceof Error ? error.message : String(error),
                    });
                }
            },
        });

    return (
        <Container size="xl" py="xl">
            <Stack gap="lg">
                <Group justify="space-between" align="flex-end" wrap="wrap">
                    <Stack gap={2}>
                        <Anchor component={Link} to="/admin/gvfg-import" size="sm">← GVFG-Import</Anchor>
                        <ChronicleHeadline as="h1">
                            {result.title ?? "GVFG-Programm"} {record.is_annex ? "· Anhang" : ""}
                        </ChronicleHeadline>
                        <Text size="sm" c="dimmed">
                            Stand {result.stand ?? "–"} · {result.entries.length} Vorhaben · Spalten{" "}
                            {result.periods.map((p) => p.label).join(", ") || "–"}
                        </Text>
                    </Stack>
                    {!confirmed && (
                        <Button onClick={handleConfirm} loading={confirm.isPending}>
                            Übernehmen
                        </Button>
                    )}
                </Group>

                {confirmed && (
                    <Alert color="teal" variant="light">
                        Übernommen am {new Date(record.confirmed_at as string).toLocaleString("de-DE")}
                        {record.confirmed_by_snapshot ? ` von ${record.confirmed_by_snapshot}` : ""}.
                    </Alert>
                )}

                {!confirmed && (
                    <Alert color="blue" variant="light" title="Neue Projekte werden als Entwurf angelegt">
                        Projekte, die der Import neu anlegt, sind Entwürfe: Sie bleiben aus Listen und Karte
                        ausgeblendet, bis sie gepflegt und fertiggestellt sind. Die Verknüpfung mit dem Vorhaben
                        und seine Förderdaten bleiben sichtbar.
                    </Alert>
                )}

                {result.warnings.length > 0 && (
                    <Alert color="yellow" variant="light" title={`${result.warnings.length} Hinweise aus der Summenprüfung`}>
                        <List size="sm" spacing={2}>
                            {result.warnings.map((w) => (
                                <List.Item key={w}>{w}</List.Item>
                            ))}
                        </List>
                    </Alert>
                )}

                <ChronicleCard>
                    <Stack gap="sm">
                        <Group gap="sm" wrap="wrap" align="flex-end">
                            <SegmentedControl
                                value={view}
                                onChange={(v) => {
                                    setView(v as "review" | "all");
                                    setPage(1);
                                }}
                                data={[
                                    { value: "review", label: `Zu prüfen (${result.entries.filter(needsReview).length})` },
                                    { value: "all", label: `Alle (${result.entries.length})` },
                                ]}
                            />
                            <Select
                                placeholder="Land"
                                data={lands}
                                value={land}
                                onChange={(v) => {
                                    setLand(v);
                                    setPage(1);
                                }}
                                clearable
                                w={220}
                            />
                            <TextInput
                                placeholder="Schlüssel oder Bezeichnung"
                                value={search}
                                onChange={(e) => {
                                    setSearch(e.currentTarget.value);
                                    setPage(1);
                                }}
                                w={240}
                            />
                            {!confirmed && withoutProject.length > 0 && (
                                <Button
                                    variant="light"
                                    size="sm"
                                    onClick={() => setCreate(new Set([...create, ...withoutProject.map((e) => e.key)]))}
                                >
                                    Für alle {withoutProject.length} ohne Projekt als Entwurf anlegen
                                </Button>
                            )}
                        </Group>

                        <ResponsiveTable minWidth={1100} striped withTableBorder verticalSpacing="xs">
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>Schlüssel</Table.Th>
                                    <Table.Th>Bezeichnung</Table.Th>
                                    <Table.Th>Fördertatbestand</Table.Th>
                                    <Table.Th ta="right">Finanzhilfen Mio. €</Table.Th>
                                    <Table.Th style={{ minWidth: 340 }}>Projekt</Table.Th>
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {pageRows.map((entry) => {
                                    const suggestion = result.suggestions.by_key[entry.key];
                                    const suggested = new Set((suggestion?.candidates ?? []).map((c) => String(c.id)));
                                    const data = options.map((o) =>
                                        suggested.has(o.value) ? { ...o, label: `${o.label} ✦` } : o,
                                    );
                                    return (
                                        <Table.Tr key={entry.key}>
                                            <Table.Td style={{ whiteSpace: "nowrap" }}>
                                                <Text size="sm" fw={500}>{entry.key}</Text>
                                                <Text size="xs" c="dimmed">
                                                    {entry.land} · {entry.kind === "db" ? "DB" : "kommunal"}
                                                    {entry.part === "nachrichtlich" ? " · nachr." : ""}
                                                </Text>
                                            </Table.Td>
                                            <Table.Td>
                                                <Text size="sm">{entry.name}</Text>
                                                {suggestion?.flags.map((flag) => (
                                                    <Badge key={flag} color="gray" variant="outline" size="xs" mr={4}>
                                                        {flag}
                                                    </Badge>
                                                ))}
                                            </Table.Td>
                                            <Table.Td>
                                                <Text size="sm">{entry.funding_type ?? "–"}</Text>
                                                <Text size="xs" c="dimmed">{entry.funding_rate != null ? `${entry.funding_rate} %` : ""}</Text>
                                            </Table.Td>
                                            <Table.Td ta="right">{formatNumberDe(aidTotal(entry))}</Table.Td>
                                            <Table.Td>
                                                <MultiSelect
                                                    data={data}
                                                    value={(current[entry.key] ?? []).map(String)}
                                                    onChange={(vals) => setProjects(entry.key, vals.map(Number))}
                                                    placeholder={create.has(entry.key) ? "wird als Entwurf angelegt" : "Projekt wählen…"}
                                                    searchable
                                                    filter={filterProjectOption}
                                                    limit={30}
                                                    size="xs"
                                                    disabled={confirmed || create.has(entry.key)}
                                                />
                                                {suggestion && SOURCE_LABEL[suggestion.source] && (
                                                    <Text size="xs" c="dimmed">Vorschlag: {SOURCE_LABEL[suggestion.source]}</Text>
                                                )}
                                                {!confirmed && (
                                                    <Group gap="xs" mt={2} wrap="wrap">
                                                        {create.has(entry.key) ? (
                                                            <>
                                                                <Badge color="blue" variant="light" size="xs">
                                                                    wird beim Übernehmen als Entwurf angelegt
                                                                </Badge>
                                                                <Anchor
                                                                    component="button"
                                                                    type="button"
                                                                    size="xs"
                                                                    onClick={() => toggleCreate(entry.key, false)}
                                                                >
                                                                    rückgängig
                                                                </Anchor>
                                                            </>
                                                        ) : (
                                                            <Button
                                                                variant="light"
                                                                size="compact-xs"
                                                                leftSection={<Plus size={12} />}
                                                                onClick={() => setDraftFor(entry)}
                                                            >
                                                                Projekt nicht gefunden – als Entwurf anlegen
                                                            </Button>
                                                        )}
                                                    </Group>
                                                )}
                                            </Table.Td>
                                        </Table.Tr>
                                    );
                                })}
                            </Table.Tbody>
                        </ResponsiveTable>
                        {rows.length === 0 && <Text c="dimmed" size="sm">Keine Vorhaben in dieser Auswahl.</Text>}
                        {rows.length > PAGE_SIZE && (
                            <Group justify="center">
                                <Pagination total={Math.ceil(rows.length / PAGE_SIZE)} value={page} onChange={setPage} />
                            </Group>
                        )}
                    </Stack>
                </ChronicleCard>
            </Stack>
            <CreateDraftProjectModal
                opened={draftFor !== null}
                onClose={() => setDraftFor(null)}
                initialName={draftFor ? (draftFor.name ?? draftFor.key) : undefined}
                sourceLabel="GVFG"
                onCreated={(project) => {
                    if (!draftFor || project.id == null) return;
                    setProjects(draftFor.key, [...(current[draftFor.key] ?? []), project.id]);
                }}
            />
        </Container>
    );
}

export default function GvfgReviewPage() {
    return (
        <RequirePermission perm="gvfg.import">
            <GvfgReviewPageContent />
        </RequirePermission>
    );
}
