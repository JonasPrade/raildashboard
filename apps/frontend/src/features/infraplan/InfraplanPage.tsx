import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
    Alert,
    Anchor,
    Container,
    Group,
    Loader,
    Pagination,
    SegmentedControl,
    Select,
    SimpleGrid,
    Stack,
    Table,
    Text,
    TextInput,
    Title,
} from "@mantine/core";
import { CompositeChart } from "@mantine/charts";
import "@mantine/charts/styles.css";
import { ChronicleCard, ChronicleDataChip, ChronicleHeadline } from "../../components/chronicle";
import {
    useInfraplanPublicKpis,
    useInfraplanPublicReports,
    useInfraplanReportEntries,
    type InfraplanPublicKpi,
    type InfraplanReportEntry,
} from "../../shared/api/queries";
import { formatDateShort } from "../../shared/format";
import { useIsMobile } from "../../shared/hooks/useBreakpoint";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import Footnotes from "./Footnotes";
import {
    KPI_CATEGORY_LABEL,
    KPI_KIND_LABEL,
    PARL_LABEL,
    SECTION_SHORT,
    buildKpiChart,
    entryCost,
    formatMio,
    groupKpis,
} from "./infraplanFormat";

const PAGE_SIZE = 50;

function KpiCard({ kpi }: { kpi: InfraplanPublicKpi }) {
    const chart = useMemo(() => buildKpiChart(kpi), [kpi]);
    const format = (v: number) =>
        `${v.toLocaleString("de-DE", { maximumFractionDigits: 2 })}${kpi.unit ? ` ${kpi.unit}` : ""}`;
    return (
        <ChronicleCard>
            <Stack gap="xs">
                <Stack gap={0}>
                    <Text fw={600} size="sm">{kpi.name}</Text>
                    {kpi.description && <Text size="xs" c="dimmed">{kpi.description}</Text>}
                </Stack>
                {chart.data.length === 0 ? (
                    <Text size="sm" c="dimmed">Noch keine geprüften Werte.</Text>
                ) : (
                    <>
                        <CompositeChart
                            h={220}
                            data={chart.data}
                            dataKey="year"
                            series={chart.series}
                            valueFormatter={format}
                            withLegend
                            legendProps={{ verticalAlign: "bottom", height: 50 }}
                            tickLine="y"
                            maxBarWidth={36}
                            barProps={{ stackId: "ist" }}
                            connectNulls
                        />
                        {chart.istReportYear && (
                            <Text size="xs" c="dimmed">
                                Ist-Werte aus dem Infraplan {chart.istReportYear}; Zielwerte je Jahrgang.
                            </Text>
                        )}
                    </>
                )}
            </Stack>
        </ChronicleCard>
    );
}

function Kpis({ kpis }: { kpis: InfraplanPublicKpi[] }) {
    const withValues = kpis.filter((k) => (k.values ?? []).length > 0);
    const groups = groupKpis(withValues);
    if (groups.length === 0) {
        return <Text size="sm" c="dimmed">Für die Kennzahlen liegen noch keine geprüften Werte vor.</Text>;
    }
    return (
        <Stack gap="xl">
            {groups.map((g) => (
                <Stack key={g.kind} gap="md">
                    <Title order={3}>{KPI_KIND_LABEL[g.kind] ?? g.kind}</Title>
                    {g.categories.map((c) => (
                        <Stack key={c.category ?? "none"} gap="xs">
                            {c.category && (
                                <Text fw={600} size="sm" c="dimmed" tt="uppercase">
                                    {KPI_CATEGORY_LABEL[c.category] ?? c.category}
                                </Text>
                            )}
                            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
                                {c.kpis.map((k) => (
                                    <KpiCard key={k.key} kpi={k} />
                                ))}
                            </SimpleGrid>
                        </Stack>
                    ))}
                </Stack>
            ))}
        </Stack>
    );
}

function projectsOf(entry: InfraplanReportEntry): { id: number; name: string }[] {
    return (entry.projects ?? [])
        .map((p) => ({ id: Number(p.id), name: String(p.name ?? `Projekt ${p.id}`) }))
        .filter((p) => Number.isFinite(p.id));
}

function Measures({ year }: { year: number }) {
    const { data: entries, isLoading, isError } = useInfraplanReportEntries(year);
    const [section, setSection] = useState<string | null>(null);
    const [search, setSearch] = useState("");
    const [page, setPage] = useState(1);

    const sections = useMemo(
        () => [...new Set((entries ?? []).map((e) => e.section))].map((s) => ({ value: s, label: SECTION_SHORT[s] ?? s })),
        [entries],
    );
    const filtered = useMemo(() => {
        const needle = search.trim().toLowerCase();
        return (entries ?? []).filter(
            (e) =>
                (!section || e.section === section) &&
                (!needle ||
                    [e.primary_number, e.bezeichnung, e.massnahme, e.laender, ...projectsOf(e).map((p) => p.name)]
                        .filter(Boolean)
                        .some((v) => String(v).toLowerCase().includes(needle))),
        );
    }, [entries, section, search]);

    if (isLoading) return <Loader size="sm" />;
    if (isError) return <Alert color="red" variant="light">Maßnahmen konnten nicht geladen werden.</Alert>;

    const pageRows = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
    return (
        <Stack gap="sm">
            <Group gap="sm" wrap="wrap">
                <Select
                    placeholder="Abschnitt"
                    data={sections}
                    value={section}
                    onChange={(v) => {
                        setSection(v);
                        setPage(1);
                    }}
                    clearable
                    w={{ base: "100%", xs: 200 }}
                />
                <TextInput
                    placeholder="Nummer, Maßnahme, Projekt"
                    value={search}
                    onChange={(e) => {
                        setSearch(e.currentTarget.value);
                        setPage(1);
                    }}
                    w={{ base: "100%", xs: 260 }}
                />
                <Text size="sm" c="dimmed">{filtered.length} Maßnahmen</Text>
            </Group>
            <ResponsiveTable minWidth={980} striped withTableBorder verticalSpacing="xs" fz="sm">
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th>Abschnitt</Table.Th>
                        <Table.Th>Maßnahme</Table.Th>
                        <Table.Th>Stand</Table.Th>
                        <Table.Th>IBN</Table.Th>
                        <Table.Th ta="right">Kosten Mio. €</Table.Th>
                        <Table.Th>Befassung</Table.Th>
                        <Table.Th>Projekt</Table.Th>
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    {pageRows.map((e) => {
                        const cost = entryCost(e);
                        const projects = projectsOf(e);
                        return (
                            <Table.Tr key={e.id}>
                                <Table.Td style={{ whiteSpace: "nowrap" }}>
                                    {SECTION_SHORT[e.section] ?? e.section}
                                    <Text size="xs" c="dimmed">Nr. {e.lfd_nr}{e.primary_number ? ` · ${e.primary_number}` : ""}</Text>
                                </Table.Td>
                                <Table.Td style={{ maxWidth: 320 }}>
                                    {e.bezeichnung ?? "–"}
                                    <Footnotes footnotes={e.footnotes} />
                                    {e.massnahme && e.massnahme !== e.bezeichnung && (
                                        <Text size="xs">{e.massnahme}</Text>
                                    )}
                                </Table.Td>
                                <Table.Td style={{ maxWidth: 180 }}>{e.state_raw ?? "–"}</Table.Td>
                                <Table.Td style={{ whiteSpace: "nowrap" }}>{e.ibn_raw ?? "–"}</Table.Td>
                                <Table.Td ta="right" style={{ whiteSpace: "nowrap" }}>
                                    {cost !== null ? formatMio(cost) : (e.cost_ref_raw ?? "–")}
                                </Table.Td>
                                <Table.Td>{e.parl_state ? (PARL_LABEL[e.parl_state] ?? e.parl_state) : (e.parl_raw ?? "–")}</Table.Td>
                                <Table.Td>
                                    {projects.length === 0 ? (
                                        <Text size="xs" c="dimmed">–</Text>
                                    ) : (
                                        <Stack gap={0}>
                                            {projects.map((p) => (
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
            {filtered.length > PAGE_SIZE && (
                <Group justify="center">
                    <Pagination total={Math.ceil(filtered.length / PAGE_SIZE)} value={page} onChange={setPage} size="sm" />
                </Group>
            )}
        </Stack>
    );
}

export default function InfraplanPage() {
    const isMobile = useIsMobile();
    const { data: reports, isLoading: reportsLoading } = useInfraplanPublicReports();
    const { data: kpis, isLoading: kpisLoading } = useInfraplanPublicKpis();
    const [year, setYear] = useState<number | null>(null);
    const current = reports?.find((r) => r.year === year) ?? reports?.[0] ?? null;

    if (reportsLoading || kpisLoading) {
        return <Container py="xl"><Group justify="center"><Loader /></Group></Container>;
    }

    return (
        <Container size="xl" pt={{ base: "md", sm: "xl" }} pb="xl" px={{ base: 0, sm: "md" }}>
            <Stack gap="xl">
                <Stack gap="xs">
                    <Group gap="xs" align="center">
                        <ChronicleHeadline as="h1">Infraplan</ChronicleHeadline>
                        {current && <ChronicleDataChip>Infraplan {current.year}</ChronicleDataChip>}
                    </Group>
                    <Text size="sm" c="dimmed">
                        Der Infraplan ist der jährlich fortgeschriebene Fünfjahresplan des Bundes für die
                        Schieneninfrastruktur. Er nennt je Maßnahme Realisierungsstand, geplante Inbetriebnahme, Kosten
                        und parlamentarische Befassung sowie Kennzahlen mit Ist- und Zielwerten. Jeder Jahrgang bleibt
                        erhalten, damit sich Kosten, Termine und Ziele über die Jahre vergleichen lassen.
                    </Text>
                </Stack>

                {!reports || reports.length === 0 ? (
                    <Alert color="gray" variant="light" title="Noch kein Infraplan eingelesen">
                        Sobald ein Jahrgang importiert und geprüft ist, erscheinen hier Kennzahlen und Maßnahmen.
                    </Alert>
                ) : (
                    <>
                        <Stack gap="md">
                            <ChronicleHeadline as="h2">Kennzahlen</ChronicleHeadline>
                            <Kpis kpis={kpis ?? []} />
                        </Stack>

                        <Stack gap="md">
                            <Group justify="space-between" align="flex-end" wrap="wrap">
                                <ChronicleHeadline as="h2">Maßnahmen</ChronicleHeadline>
                                {reports.length > 1 && (
                                    <SegmentedControl
                                        data={reports.map((r) => ({ value: String(r.year), label: String(r.year) }))}
                                        value={String(current?.year ?? "")}
                                        onChange={(v) => setYear(Number(v))}
                                        fullWidth={isMobile}
                                    />
                                )}
                            </Group>
                            {current && (
                                <Text size="sm" c="dimmed">
                                    {current.title ?? `Infraplan ${current.year}`}
                                    {current.published_on ? `, veröffentlicht ${formatDateShort(current.published_on)}` : ""}
                                    {` · ${current.entry_count} Maßnahmen`}
                                </Text>
                            )}
                            {current && <Measures key={current.year} year={current.year} />}
                        </Stack>
                    </>
                )}
            </Stack>
        </Container>
    );
}
