import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
    Anchor,
    Badge,
    Checkbox,
    Group,
    Pagination,
    Paper,
    SegmentedControl,
    Select,
    Stack,
    Table,
    Text,
    TextInput,
} from "@mantine/core";
import { Stat, StatBand } from "../../shared/ui/Stat";
import { useGvfgProgramEntries, useGvfgPrograms, type GvfgEntry } from "../../shared/api/queries";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import { CATEGORY_LABEL, KIND_LABEL, categories, editionLabel, formatMio, num, plannedAid, sumLine } from "./gvfgFormat";
import { LoadingState } from "../../shared/ui/LoadingState";
import { ErrorState } from "../../shared/ui/ErrorState";

const PAGE_SIZE = 50;

type KindFilter = "all" | "kommunal" | "db";
type PartFilter = "all" | "finanzrelevant" | "nachrichtlich";

function sum(entries: GvfgEntry[], field: "cost_total" | "aid_total"): number {
    return entries.reduce((acc, e) => acc + (num(sumLine(e)?.[field]) ?? 0), 0);
}

export default function GvfgOverviewPage() {
    const { data: programs, isLoading: programsLoading } = useGvfgPrograms();
    const [programId, setProgramId] = useState<number | null>(null);
    const program = programs?.find((p) => p.id === programId) ?? programs?.[0] ?? null;
    const { data: entries, isLoading, isError, refetch } = useGvfgProgramEntries(program?.id ?? null);

    const [land, setLand] = useState<string | null>(null);
    const [kind, setKind] = useState<KindFilter>("all");
    const [part, setPart] = useState<PartFilter>("all");
    const [fundingType, setFundingType] = useState<string | null>(null);
    const [withoutProject, setWithoutProject] = useState(false);
    const [search, setSearch] = useState("");
    const [page, setPage] = useState(1);

    const lands = useMemo(() => [...new Set((entries ?? []).map((e) => e.land))].sort(), [entries]);
    const fundingTypes = useMemo(
        () => [...new Set((entries ?? []).map((e) => e.funding_type).filter((t): t is string => !!t))].sort(),
        [entries],
    );
    const filtered = useMemo(() => {
        const needle = search.trim().toLowerCase();
        return (entries ?? []).filter(
            (e) =>
                (!land || e.land === land) &&
                (kind === "all" || e.kind === kind) &&
                (part === "all" || e.part === part) &&
                (!fundingType || e.funding_type === fundingType) &&
                (!withoutProject || e.projects.length === 0) &&
                (!needle ||
                    e.key.toLowerCase().includes(needle) ||
                    (e.name ?? "").toLowerCase().includes(needle) ||
                    (e.city ?? "").toLowerCase().includes(needle)),
        );
    }, [entries, land, kind, part, fundingType, withoutProject, search]);
    const byLand = useMemo(() => {
        const groups = new Map<string, GvfgEntry[]>();
        for (const e of filtered) groups.set(e.land, [...(groups.get(e.land) ?? []), e]);
        return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
    }, [filtered]);

    const resetPage = <T,>(setter: (v: T) => void) => (v: T) => {
        setter(v);
        setPage(1);
    };

    if (programsLoading) return <LoadingState rows={6} />;
    if (!program) {
        return (
            <Text c="dimmed" py="xl">
                Noch kein GVFG-Bundesprogramm importiert.
            </Text>
        );
    }

    const pageRows = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
    const planned = program.periods.filter((p) => p.kind === "geplant").map((p) => p.label);
    const plannedSum = filtered.reduce((acc, e) => acc + (plannedAid(e, program) ?? 0), 0);

    return (
        <Stack gap="lg" py="lg">
            <Group gap="sm" wrap="wrap" align="flex-end">
                <Select
                    label="Ausgabe"
                    data={(programs ?? []).map((p) => ({ value: String(p.id), label: editionLabel(p) }))}
                    value={String(program.id)}
                    onChange={(v) => {
                        setProgramId(v ? Number(v) : null);
                        setPage(1);
                    }}
                    allowDeselect={false}
                    w={160}
                />
                <Text size="sm" c="dimmed" pb={6}>
                    {program.title}
                    {program.stand ? ` · Stand ${new Date(program.stand).toLocaleDateString("de-DE")}` : ""}
                    {program.has_annex ? " · mit Anhang" : ""}
                </Text>
            </Group>

            <Group gap="sm" wrap="wrap" align="flex-end">
                <TextInput
                    placeholder="Schlüssel, Bezeichnung oder Ort"
                    value={search}
                    onChange={(e) => resetPage(setSearch)(e.currentTarget.value)}
                    flex="1 1 240px"
                />
                <Select placeholder="Land" data={lands} value={land} onChange={resetPage(setLand)} clearable w={200} />
                <Select
                    placeholder="Fördertatbestand"
                    data={fundingTypes}
                    value={fundingType}
                    onChange={resetPage(setFundingType)}
                    clearable
                    w={220}
                />
                <SegmentedControl
                    value={kind}
                    onChange={(v) => resetPage(setKind)(v as KindFilter)}
                    data={[
                        { value: "all", label: "Alle" },
                        { value: "kommunal", label: "kommunal" },
                        { value: "db", label: "DB" },
                    ]}
                />
                <SegmentedControl
                    value={part}
                    onChange={(v) => resetPage(setPart)(v as PartFilter)}
                    data={[
                        { value: "all", label: "Alle Teile" },
                        { value: "finanzrelevant", label: "finanzrelevant" },
                        { value: "nachrichtlich", label: "nachrichtlich" },
                    ]}
                />
                <Checkbox
                    label="ohne Projekt"
                    checked={withoutProject}
                    onChange={(e) => resetPage(setWithoutProject)(e.currentTarget.checked)}
                />
            </Group>

            {isLoading && <LoadingState rows={6} />}
            {isError && <ErrorState onRetry={() => void refetch()}>Vorhaben konnten nicht geladen werden.</ErrorState>}

            {!isLoading && !isError && (
                <>
                    <StatBand columns={4}>
                        <Stat title="Vorhaben" value={String(filtered.length)} />
                        <Stat title="Gesamtkosten (Mio. €)" value={formatMio(sum(filtered, "cost_total"))} />
                        <Stat title="Bundesfinanzhilfen (Mio. €)" value={formatMio(sum(filtered, "aid_total"))} />
                        <Stat
                            title={planned.length ? `davon ${planned[0]}–${planned[planned.length - 1]}` : "davon geplant"}
                            value={formatMio(plannedSum)}
                        />
                    </StatBand>

                    <Paper withBorder p="var(--card-pad)">
                        <ResponsiveTable minWidth={1000} striped highlightOnHover verticalSpacing="xs">
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>Schlüssel</Table.Th>
                                    <Table.Th>Vorhaben</Table.Th>
                                    <Table.Th>Fördertatbestand</Table.Th>
                                    <Table.Th>Kat.</Table.Th>
                                    <Table.Th className="num">Gesamtkosten</Table.Th>
                                    <Table.Th className="num">Finanzhilfen</Table.Th>
                                    <Table.Th className="num">davon geplant</Table.Th>
                                    <Table.Th>Projekt</Table.Th>
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {pageRows.map((e) => {
                                    const total = sumLine(e);
                                    return (
                                        <Table.Tr key={e.id}>
                                            <Table.Td style={{ whiteSpace: "nowrap" }}>
                                                <Text size="sm" fw={500}>{e.key}</Text>
                                                <Text size="xs" c="dimmed">
                                                    {e.land} · {KIND_LABEL[e.kind] ?? e.kind}
                                                    {e.part === "nachrichtlich" ? " · nachr." : ""}
                                                </Text>
                                            </Table.Td>
                                            <Table.Td>
                                                <Text size="sm">{e.name}</Text>
                                                {e.city && <Text size="xs" c="dimmed">{e.city}</Text>}
                                            </Table.Td>
                                            <Table.Td>
                                                <Text size="sm">{e.funding_type ?? "–"}</Text>
                                                <Text size="xs" c="dimmed">{e.funding_rate != null ? `${e.funding_rate} %` : ""}</Text>
                                            </Table.Td>
                                            <Table.Td>{e.part === "finanzrelevant" ? categories(e) : "–"}</Table.Td>
                                            <Table.Td className="num">{formatMio(total?.cost_total)}</Table.Td>
                                            <Table.Td className="num">{formatMio(total?.aid_total)}</Table.Td>
                                            <Table.Td className="num">
                                                {e.part === "finanzrelevant" ? formatMio(plannedAid(e, program)) : "–"}
                                            </Table.Td>
                                            <Table.Td>
                                                {e.projects.length === 0 ? (
                                                    <Text size="xs" c="dimmed">–</Text>
                                                ) : (
                                                    <Stack gap={2}>
                                                        {e.projects.map((p) => (
                                                            <Anchor key={p.id} component={Link} to={`/projects/${p.id}`} size="sm">
                                                                {p.name}
                                                            </Anchor>
                                                        ))}
                                                    </Stack>
                                                )}
                                            </Table.Td>
                                        </Table.Tr>
                                    );
                                })}
                            </Table.Tbody>
                        </ResponsiveTable>
                        {filtered.length === 0 && <Text c="dimmed" size="sm" py="md">Keine Vorhaben in dieser Auswahl.</Text>}
                        {filtered.length > PAGE_SIZE && (
                            <Group justify="center" pt="sm">
                                <Pagination total={Math.ceil(filtered.length / PAGE_SIZE)} value={page} onChange={setPage} />
                            </Group>
                        )}
                    </Paper>

                    <Paper withBorder p="var(--card-pad)">
                        <Stack gap="xs">
                            <Text fw={600}>Summen je Land</Text>
                            <ResponsiveTable minWidth={560} striped verticalSpacing="xs">
                                <Table.Thead>
                                    <Table.Tr>
                                        <Table.Th>Land</Table.Th>
                                        <Table.Th className="num">Vorhaben</Table.Th>
                                        <Table.Th className="num">Gesamtkosten</Table.Th>
                                        <Table.Th className="num">Finanzhilfen</Table.Th>
                                    </Table.Tr>
                                </Table.Thead>
                                <Table.Tbody>
                                    {byLand.map(([name, rows]) => (
                                        <Table.Tr key={name}>
                                            <Table.Td>{name}</Table.Td>
                                            <Table.Td className="num">{rows.length}</Table.Td>
                                            <Table.Td className="num">{formatMio(sum(rows, "cost_total"))}</Table.Td>
                                            <Table.Td className="num">{formatMio(sum(rows, "aid_total"))}</Table.Td>
                                        </Table.Tr>
                                    ))}
                                </Table.Tbody>
                            </ResponsiveTable>
                            <Text size="xs" c="dimmed">
                                Beträge in Mio. € (∑-Zeile je Vorhaben). {CATEGORY_LABEL.A}: endgültig, {CATEGORY_LABEL.B}:
                                vorläufig, {CATEGORY_LABEL.C}: bedingt aufgenommen. <Badge variant="outline">nachr.</Badge>{" "}
                                = nachrichtlicher Teil ohne eingeplante Finanzhilfen.
                            </Text>
                        </Stack>
                    </Paper>
                </>
            )}
        </Stack>
    );
}
