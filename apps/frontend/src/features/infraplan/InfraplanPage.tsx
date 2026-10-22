import { createRef, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Info } from "lucide-react";
import {
    ActionIcon,
    Alert,
    Badge,
    Button,
    Container,
    Group,
    Modal,
    Pagination,
    Paper,
    Progress,
    SegmentedControl,
    Select,
    SimpleGrid,
    Stack,
    Text,
    TextInput,
    Title,
    Tooltip,
} from "@mantine/core";
import { ChartTooltip, CompositeChart } from "@mantine/charts";
import "@mantine/charts/styles.css";
import "../../shared/ui/charts.css";
import {
    useInfraplanPublicKpis,
    useInfraplanPublicReports,
    useInfraplanReportEntries,
    type InfraplanPublicKpi,
    type InfraplanReportEntry,
} from "../../shared/api/queries";
import { formatDateShort } from "../../shared/format";
import { useIsMobile } from "../../shared/hooks/useBreakpoint";
import { LinkedProjects, type LinkedProject } from "../../shared/ui/LinkedProjects";
import { ProjectRegister, type RegisterSection } from "../projects/ProjectRegister";
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
    kpisAsOf,
    stackTotal,
    zoomedDomain,
    type KpiChartScope,
    type KpiCompanion,
    type KpiChartSeries,
} from "./infraplanFormat";
import { LoadingState } from "../../shared/ui/LoadingState";
import { ErrorState } from "../../shared/ui/ErrorState";
import ProjectHoverCard from "../projects/ProjectHoverCard";

const PAGE_SIZE = 25;

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
    return (
        <Modal opened={opened} onClose={onClose} title={kpi.name} size="xl">
            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
                {subSeries.map((s) => (
                    <Paper withBorder p="var(--card-pad)" key={s}>
                        <Stack gap="xs">
                            <Text fw={600} size="sm">{s}</Text>
                            <KpiChart kpi={kpi} scope={{ series: s }} companion={companion} h={200} />
                        </Stack>
                    </Paper>
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
                <Info size={16} />
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
        <Paper withBorder p="var(--card-pad)">
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
        </Paper>
    );
}

type SectionRef = React.RefObject<HTMLDivElement | null>;

function Kpis({ kpis }: { kpis: InfraplanPublicKpi[] }) {
    // Companion KPIs are drawn inside their main KPI's chart, not on their own.
    const groups = useMemo(() => {
        const hidden = companionKeys(kpis);
        return groupKpis(kpis.filter((k) => (k.values ?? []).length > 0 && !hidden.has(k.key)));
    }, [kpis]);
    const companions = useMemo(() => kpiCompanions(kpis), [kpis]);
    // One scroll target per Bereich: the kind, and each category below it.
    const tocSections = useMemo<RegisterSection[]>(
        () =>
            groups.flatMap((g) => [
                { id: g.kind, label: KPI_KIND_LABEL[g.kind] ?? g.kind, ref: createRef<HTMLDivElement>() as SectionRef, visible: true },
                ...g.categories
                    .filter((c) => c.category)
                    .map((c) => ({
                        id: `${g.kind}:${c.category}`,
                        label: KPI_CATEGORY_LABEL[c.category!] ?? c.category!,
                        ref: createRef<HTMLDivElement>() as SectionRef,
                        visible: true,
                        level: 2 as const,
                    })),
            ]),
        [groups],
    );
    const refOf = (id: string) => tocSections.find((s) => s.id === id)?.ref;
    if (groups.length === 0) {
        return <Text size="sm" c="dimmed">Für die Kennzahlen liegen noch keine geprüften Werte vor.</Text>;
    }
    return (
        <div className="project-register-layout">
            <ProjectRegister sections={tocSections} />
            <Stack gap="xl">
                {groups.map((g) => (
                    <Stack key={g.kind} gap="md" ref={refOf(g.kind)} style={{ scrollMarginTop: 80 }}>
                        <Title order={3}>{KPI_KIND_LABEL[g.kind] ?? g.kind}</Title>
                        {g.categories.map((c) => (
                            <Stack
                                key={c.category ?? "none"}
                                gap="xs"
                                ref={c.category ? refOf(`${g.kind}:${c.category}`) : undefined}
                                style={{ scrollMarginTop: 80 }}
                            >
                                {c.category && (
                                    <Text className="idt-eyebrow" component="div">
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
        </div>
    );
}

function projectsOf(entry: InfraplanReportEntry): LinkedProject[] {
    return (entry.projects ?? [])
        .map((p) => ({ id: Number(p.id), name: String(p.name ?? `Projekt ${p.id}`) }))
        .filter((p) => Number.isFinite(p.id));
}

function Fact({ label, value }: { label: string; value: React.ReactNode }) {
    return (
        <Stack gap={2} align="flex-end" maw={180}>
            <Text size="xs" c="dimmed">{label}</Text>
            <Text size="sm" fw={600} ta="right">{value}</Text>
        </Stack>
    );
}

/** One Maßnahme, laid out like a FinVe card. */
function MeasureCard({ entry }: { entry: InfraplanReportEntry }) {
    const cost = entryCost(entry);
    return (
        <Paper withBorder p="var(--card-pad)">
            <Stack gap="md">
                <Group justify="space-between" align="flex-start" wrap="wrap" gap="sm">
                    <Stack gap={4} style={{ flex: "1 1 280px", minWidth: 0 }}>
                        <Group gap="sm" align="center">
                            <Badge variant="outline">{SECTION_SHORT[entry.section] ?? entry.section}</Badge>
                            <Badge variant="outline">Nr. {entry.lfd_nr}</Badge>
                            {entry.primary_number && <Badge variant="outline">{entry.primary_number}</Badge>}
                        </Group>
                        <Text fw={600} size="md" lh={1.3}>
                            {entry.bezeichnung ?? "–"}
                            <Footnotes footnotes={entry.footnotes} />
                        </Text>
                        {entry.massnahme && entry.massnahme !== entry.bezeichnung && (
                            <Text size="sm" c="dimmed">{entry.massnahme}</Text>
                        )}
                    </Stack>
                    <Group gap="lg" align="flex-start" wrap="wrap">
                        <Fact label="Stand" value={entry.state_raw ?? "–"} />
                        <Fact label="IBN" value={entry.ibn_raw ?? "–"} />
                        <Fact label="Kosten Mio. €" value={cost !== null ? formatMio(cost) : (entry.cost_ref_raw ?? "–")} />
                        <Fact
                            label="Befassung"
                            value={entry.parl_state ? (PARL_LABEL[entry.parl_state] ?? entry.parl_state) : (entry.parl_raw ?? "–")}
                        />
                    </Group>
                </Group>
                <LinkedProjects
                    projects={projectsOf(entry)}
                    wrapLink={(id, link) => <ProjectHoverCard projectId={id}>{link}</ProjectHoverCard>}
                />
            </Stack>
        </Paper>
    );
}

function Measures({ year }: { year: number }) {
    const { data: entries, isLoading, isError, refetch } = useInfraplanReportEntries(year);
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

    if (isLoading) return <LoadingState rows={6} />;
    if (isError) return <ErrorState onRetry={() => void refetch()}>Maßnahmen konnten nicht geladen werden.</ErrorState>;

    const pageRows = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
    return (
        <Stack gap="md">
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
                    flex="1 1 260px"
                />
            </Group>
            <Text size="sm" c="dimmed">{filtered.length} von {(entries ?? []).length} Maßnahmen</Text>
            {filtered.length === 0 && (
                <Text c="dimmed" ta="center" py="xl">Keine Maßnahmen gefunden.</Text>
            )}
            {pageRows.map((e) => (
                <MeasureCard key={e.id} entry={e} />
            ))}
            {filtered.length > PAGE_SIZE && (
                <Group justify="center">
                    <Pagination total={Math.ceil(filtered.length / PAGE_SIZE)} value={page} onChange={setPage} size="sm" />
                </Group>
            )}
        </Stack>
    );
}

type View = "kennzahlen" | "massnahmen";

export default function InfraplanPage() {
    const isMobile = useIsMobile();
    const [searchParams, setSearchParams] = useSearchParams();
    const { data: reports, isLoading: reportsLoading } = useInfraplanPublicReports();
    const { data: kpis, isLoading: kpisLoading } = useInfraplanPublicKpis();
    const view: View = searchParams.get("view") === "massnahmen" ? "massnahmen" : "kennzahlen";
    const year = Number(searchParams.get("jahr")) || null;
    const current = reports?.find((r) => r.year === year) ?? reports?.[0] ?? null;
    // Targets are compared with the Jahrgang before the chosen one.
    const compareYear =
        (reports ?? []).map((r) => r.year).filter((y) => current && y < current.year).sort((a, b) => b - a)[0] ?? null;
    const kpisForYear = useMemo(
        () => (current ? kpisAsOf(kpis ?? [], current.year, compareYear) : (kpis ?? [])),
        [kpis, current, compareYear],
    );

    const setParam = (key: string, value: string | null) =>
        setSearchParams(
            (prev) => {
                if (value) prev.set(key, value);
                else prev.delete(key);
                return prev;
            },
            { replace: true },
        );

    if (reportsLoading || kpisLoading) {
        return <Container py="xl"><LoadingState rows={6} /></Container>;
    }

    return (
        <Container size="xl" pt={{ base: "md", sm: "xl" }} pb="xl" px={{ base: 0, sm: "md" }}>
            <Stack gap="xl">
                <Group justify="space-between" align="center" wrap="wrap" gap="sm">
                    <Group gap="xs" align="center" wrap="nowrap">
                        <Title order={1}>Infraplan</Title>
                        <Tooltip
                            label="Der Infraplan ist der jährlich fortgeschriebene Fünfjahresplan des Bundes für die
                                Schieneninfrastruktur. Er nennt je Maßnahme Realisierungsstand, geplante Inbetriebnahme,
                                Kosten und parlamentarische Befassung sowie Kennzahlen mit Ist- und Zielwerten. Jeder
                                Jahrgang bleibt erhalten, damit sich Kosten, Termine und Ziele über die Jahre vergleichen
                                lassen."
                            multiline
                            w={320}
                            withArrow
                            events={{ hover: true, focus: true, touch: true }}
                        >
                            <ActionIcon variant="subtle" color="gray" size="md" aria-label="Was ist der Infraplan?">
                                <Info size={16} />
                            </ActionIcon>
                        </Tooltip>
                    </Group>
                    {reports && reports.length > 1 ? (
                        <Select
                            aria-label="Jahrgang"
                            data={reports.map((r) => ({ value: String(r.year), label: `Infraplan ${r.year}` }))}
                            value={String(current?.year ?? "")}
                            onChange={(v) => setParam("jahr", v)}
                            allowDeselect={false}
                            w={{ base: "100%", xs: 180 }}
                        />
                    ) : (
                        current && <Badge variant="outline">Infraplan {current.year}</Badge>
                    )}
                </Group>

                {!reports || reports.length === 0 ? (
                    <Alert color="gray" variant="light" title="Noch kein Infraplan eingelesen">
                        Sobald ein Jahrgang importiert und geprüft ist, erscheinen hier Kennzahlen und Maßnahmen.
                    </Alert>
                ) : (
                    <>
                        <Group justify="center">
                            <SegmentedControl
                                value={view}
                                onChange={(v) => setParam("view", v === "massnahmen" ? v : null)}
                                size="md"
                                fullWidth={isMobile}
                                style={isMobile ? { flex: 1, minWidth: 0 } : { minWidth: 300 }}
                                data={[
                                    { value: "kennzahlen", label: "Kennzahlen" },
                                    { value: "massnahmen", label: "Maßnahmen" },
                                ]}
                            />
                        </Group>

                        {view === "kennzahlen" ? (
                            <Stack gap="md">
                                {current && (
                                    <Text size="sm" c="dimmed">
                                        Ist- und Zielwerte aus dem Infraplan {current.year}
                                        {compareYear
                                            ? `, im Vergleich zu den Zielen des Infraplans ${compareYear} (gestrichelt).`
                                            : "."}
                                    </Text>
                                )}
                                <Kpis kpis={kpisForYear} />
                            </Stack>
                        ) : (
                            current && (
                                <Stack gap="md">
                                    <Text size="sm" c="dimmed">
                                        {current.title ?? `Infraplan ${current.year}`}
                                        {current.published_on ? `, veröffentlicht ${formatDateShort(current.published_on)}` : ""}
                                    </Text>
                                    <Measures key={current.year} year={current.year} />
                                </Stack>
                            )
                        )}
                    </>
                )}
            </Stack>
        </Container>
    );
}
