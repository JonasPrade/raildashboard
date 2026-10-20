import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
    ActionIcon,
    Alert,
    Anchor,
    Button,
    Container,
    Group,
    Loader,
    Modal,
    Pagination,
    Progress,
    SegmentedControl,
    Select,
    SimpleGrid,
    Stack,
    Table,
    Text,
    TextInput,
    Title,
    Tooltip,
} from "@mantine/core";
import { ChartTooltip, CompositeChart } from "@mantine/charts";
import { IconInfoCircle } from "@tabler/icons-react";
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
    STACK_TOTAL_KEY,
    KPI_KIND_LABEL,
    PARL_LABEL,
    SECTION_SHORT,
    buildKpiChart,
    entryCost,
    formatMio,
    groupKpis,
    companionKeys,
    kpiCompanions,
    kpiFlow,
    kpiOverview,
    stackTotal,
    zoomedDomain,
    type KpiChartScope,
    type KpiCompanion,
    type KpiChartSeries,
} from "./infraplanFormat";

const PAGE_SIZE = 50;

const formatNumber = (v: number) => v.toLocaleString("de-DE", { maximumFractionDigits: 2 });
const withUnit = (unit: string | null | undefined) => (v: number) => `${formatNumber(v)}${unit ? ` ${unit}` : ""}`;
// Longer units ("Mio. Trkm") wrap on the axis; they stand under the title instead.
const axisUnit = (unit: string | null | undefined) => (unit && unit.length <= 2 ? unit : null);

function KpiChart({ kpi, scope, companion, stacked = true, compact = false, h = 220 }: {
    kpi: InfraplanPublicKpi;
    scope: KpiChartScope;
    companion?: KpiCompanion;
    stacked?: boolean;
    /** Small multiple: no caption (the card has one), a plain 0–100 % axis. */
    compact?: boolean;
    h?: number;
}) {
    const chart = useMemo(() => buildKpiChart(kpi, scope, companion), [kpi, scope, companion]);
    const hasRight = chart.series.some((s) => s.yAxisId === "right");
    // Units travel per series into the tooltip, so the shared formatter stays unit-free.
    const perSeries = (s: KpiChartSeries) => ({
        stackId: s.yAxisId === "right" ? "right" : stacked ? "ist" : undefined,
        unit: s.unit ? ` ${s.unit}` : undefined,
    });
    const domain = useMemo(() => (kpi.zoomed_axis ? zoomedDomain(chart, kpi.unit) : null), [kpi.zoomed_axis, kpi.unit, chart]);
    const tooltipSeries = useMemo(
        () => [...chart.series, { name: STACK_TOTAL_KEY, label: "Summe", color: "transparent" }],
        [chart.series],
    );
    if (chart.data.length === 0) return <Text size="sm" c="dimmed">Keine geprüften Werte.</Text>;
    return (
        <>
            <CompositeChart
                h={h}
                data={chart.data}
                dataKey="year"
                series={chart.series}
                valueFormatter={formatNumber}
                yAxisProps={{
                    tickFormatter: withUnit(axisUnit(kpi.unit)),
                    // Room for "1.000 km" without wrapping.
                    width: axisUnit(kpi.unit) ? 72 : 56,
                    ...(domain ? { domain, allowDataOverflow: true } : {}),
                    ...(compact && kpi.unit === "%" ? { domain: [0, 100], ticks: [0, 50, 100] } : {}),
                }}
                withRightYAxis={hasRight}
                rightYAxisProps={{ tickFormatter: withUnit(axisUnit(companion?.unit)), width: 56 }}
                withLegend={chart.series.length > 1}
                // Long legends wrap to a second row; leave room so they do not run into the caption.
                legendProps={{ verticalAlign: "bottom", height: chart.series.length > 3 ? 80 : 50 }}
                tickLine="y"
                maxBarWidth={36}
                barProps={(s) => perSeries(s as KpiChartSeries)}
                lineProps={(s) => ({ unit: perSeries(s as KpiChartSeries).unit })}
                connectNulls
                tooltipProps={{
                    content: ({ label, payload }) => {
                        const items = [...(payload ?? [])];
                        const total = stacked ? stackTotal(items, chart.series) : null;
                        // Stacked bars get a closing "Summe" row.
                        const rows =
                            total === null
                                ? items
                                : [
                                      ...items,
                                      {
                                          name: STACK_TOTAL_KEY,
                                          dataKey: STACK_TOTAL_KEY,
                                          value: total,
                                          color: "transparent",
                                          unit: kpi.unit ? ` ${kpi.unit}` : undefined,
                                          payload: { [STACK_TOTAL_KEY]: total },
                                      },
                                  ];
                        return (
                            <ChartTooltip
                                label={label}
                                payload={rows}
                                series={tooltipSeries}
                                valueFormatter={formatNumber}
                            />
                        );
                    },
                }}
            />
            {chart.istReportYear && !compact && (
                <Text size="xs" c="dimmed">
                    Ist-Werte aus dem Infraplan {chart.istReportYear}; Zielwerte je Jahrgang.
                    {companion && ` ${companion.label} auf der rechten Skala.`}
                    {domain && ` Skala beginnt bei ${withUnit(kpi.unit)(domain[0])}, nicht bei 0.`}
                </Text>
            )}
        </>
    );
}

/** One chart per sub-series, so each category's Ist and targets can be traced on their own. */
function KpiDetailModal({ kpi, companion, subSeries, opened, onClose }: {
    kpi: InfraplanPublicKpi;
    companion?: KpiCompanion;
    subSeries: string[];
    opened: boolean;
    onClose: () => void;
}) {
    const isMobile = useIsMobile();
    return (
        <Modal opened={opened} onClose={onClose} title={kpi.name} size="xl" fullScreen={isMobile}>
            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
                {subSeries.map((s) => (
                    <ChronicleCard key={s}>
                        <Stack gap="xs">
                            <Text fw={600} size="sm">{s}</Text>
                            <KpiChart kpi={kpi} scope={{ series: s }} companion={companion} h={200} />
                        </Stack>
                    </ChronicleCard>
                ))}
            </SimpleGrid>
        </Modal>
    );
}

/** Herkunft and Einsatz of one year as two ranked lists with share bars. */
function KpiFlowView({ kpi }: { kpi: InfraplanPublicKpi }) {
    const flow = useMemo(() => kpiFlow(kpi), [kpi]);
    if (!flow) return <Text size="sm" c="dimmed">Keine geprüften Werte.</Text>;
    const format = withUnit(kpi.unit);
    const side = (title: string, items: { label: string; value: number }[], color: string) => {
        const total = items.reduce((a, b) => a + b.value, 0);
        return (
            <Stack gap={6}>
                <Group justify="space-between">
                    <Text fw={600} size="sm">{title}</Text>
                    <Text fw={600} size="sm">{format(total)}</Text>
                </Group>
                {items.map((i) => (
                    <Stack key={i.label} gap={2}>
                        <Group justify="space-between" wrap="nowrap" gap="xs">
                            <Text size="xs">{i.label}</Text>
                            <Text size="xs" style={{ whiteSpace: "nowrap" }}>{format(i.value)}</Text>
                        </Group>
                        <Progress value={total ? (i.value / total) * 100 : 0} color={color} size="sm" />
                    </Stack>
                ))}
            </Stack>
        );
    };
    return (
        <Stack gap="xs">
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg">
                {side("Herkunft", flow.herkunft, "blue.6")}
                {side("Einsatz", flow.einsatz, "teal.6")}
            </SimpleGrid>
            <Text size="xs" c="dimmed">Ist {flow.year}; Rundungsdifferenzen möglich.</Text>
        </Stack>
    );
}

/** Short explanation of a KPI (admin "Beschreibung") behind an info icon next to its name. */
function KpiInfo({ description }: { description: string }) {
    return (
        <Tooltip label={description} multiline w={280} withArrow position="top" events={{ hover: true, focus: true, touch: true }}>
            <ActionIcon variant="subtle" color="gray" size="sm" aria-label="Erklärung der Kennzahl">
                <IconInfoCircle size={16} />
            </ActionIcon>
        </Tooltip>
    );
}

function KpiCard({ kpi, companion }: { kpi: InfraplanPublicKpi; companion?: KpiCompanion }) {
    const overview = useMemo(() => kpiOverview(kpi), [kpi]);
    const [detailOpen, setDetailOpen] = useState(false);
    const hasDetails = overview.layout === "chart" && overview.detailSeries.length > 0;
    // The flow lists show a single year; it belongs in the heading, not just in the footnote.
    const flowYear = overview.layout === "flow" ? kpiFlow(kpi)?.year : undefined;
    return (
        <ChronicleCard>
            <Stack gap="xs">
                <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm">
                    <Stack gap={0}>
                        <Group gap={4} wrap="nowrap" align="center">
                            <Text fw={600} size="sm">{flowYear ? `${kpi.name} ${flowYear}` : kpi.name}</Text>
                            {kpi.description && <KpiInfo description={kpi.description} />}
                        </Group>
                        {(overview.note || (kpi.unit && !axisUnit(kpi.unit))) && (
                            <Text size="xs" c="dimmed">
                                {[overview.note, kpi.unit && !axisUnit(kpi.unit) ? `in ${kpi.unit}` : null]
                                    .filter(Boolean)
                                    .join(" · ")}
                            </Text>
                        )}
                    </Stack>
                    {hasDetails && (
                        <Button size="compact-xs" variant="light" onClick={() => setDetailOpen(true)} style={{ flexShrink: 0 }}>
                            Details
                        </Button>
                    )}
                </Group>
                {(kpi.values ?? []).length === 0 ? (
                    <Text size="sm" c="dimmed">Noch keine geprüften Werte.</Text>
                ) : overview.layout === "flow" ? (
                    <KpiFlowView kpi={kpi} />
                ) : overview.layout === "split" ? (
                    <Stack gap="xs">
                        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
                            {overview.detailSeries.map((s) => (
                                <Stack key={s} gap={4}>
                                    <Text size="xs" fw={600}>{s}</Text>
                                    <KpiChart kpi={kpi} scope={{ series: s }} compact h={140} />
                                </Stack>
                            ))}
                        </SimpleGrid>
                        <Text size="xs" c="dimmed">Ist-Werte aus dem Infraplan; je Merkmal ein eigener Anteil.</Text>
                    </Stack>
                ) : (
                    <KpiChart kpi={kpi} scope={overview.scope} companion={companion} stacked={overview.stacked} />
                )}
            </Stack>
            {hasDetails && (
                <KpiDetailModal
                    kpi={kpi}
                    companion={companion}
                    subSeries={overview.detailSeries}
                    opened={detailOpen}
                    onClose={() => setDetailOpen(false)}
                />
            )}
        </ChronicleCard>
    );
}

function Kpis({ kpis }: { kpis: InfraplanPublicKpi[] }) {
    // Companion KPIs are drawn inside their main KPI's chart, not on their own.
    const hidden = companionKeys(kpis);
    const withValues = kpis.filter((k) => (k.values ?? []).length > 0 && !hidden.has(k.key));
    const groups = groupKpis(withValues);
    const companions = useMemo(() => kpiCompanions(kpis), [kpis]);
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
                                    // Small multiples and the flow lists need the full row.
                                    <div key={k.key} style={k.chart_layout === "split" || k.chart_layout === "flow" ? { gridColumn: "1 / -1" } : undefined}>
                                        <KpiCard kpi={k} companion={companions.get(k.key)} />
                                    </div>
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
