import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Anchor, Badge, Collapse, Group, Paper, Stack, Table, Text, Title } from "@mantine/core";
import { BarChart } from "@mantine/charts";
import "../../../shared/ui/charts.css";
import { CHART_SERIES } from "../../../shared/theme/semanticColors";
import "@mantine/charts/styles.css";
import { Link } from "react-router-dom";
import { type GvfgProjectEntry, useProjectGvfg } from "../../../shared/api/queries";
import { ResponsiveTable } from "../../../shared/ui/ResponsiveTable";
import { CATEGORY_LABEL, KIND_LABEL, editionLabel, formatMio, num, sumLine } from "../../gvfg/gvfgFormat";
import { LoadingState } from "../../../shared/ui/LoadingState";
import ProjectHoverCard from "../ProjectHoverCard";

// ---------------------------------------------------------------------------
// GVFG-Bundesprogramm on the project page (docs/features/feature-gvfg-import.md).
// The newest edition is shown in full; older editions only as a development
// of the totals. A parent lists its subprojects' entries as links — no sums,
// because a parent's own entry and its children's may overlap.
// ---------------------------------------------------------------------------

/** Entries grouped by key, newest edition first in each group. */
function byKey(entries: GvfgProjectEntry[]): GvfgProjectEntry[][] {
    const groups = new Map<string, GvfgProjectEntry[]>();
    for (const e of entries) groups.set(e.key, [...(groups.get(e.key) ?? []), e]);
    return [...groups.values()].map((g) => [...g].sort((a, b) => b.program.year_from - a.program.year_from));
}

function Fact({ label, value }: { label: string; value: string | number | null | undefined }) {
    if (value === null || value === undefined || value === "") return null;
    return (
        <Stack gap={0}>
            <Text size="xs" c="dimmed">{label}</Text>
            <Text size="sm" fw={500}>{value}</Text>
        </Stack>
    );
}

function AmountTable({ entry }: { entry: GvfgProjectEntry }) {
    const periods = entry.program.periods;
    const informational = entry.part === "nachrichtlich";
    return (
        <ResponsiveTable minWidth={informational ? 360 : 720} striped verticalSpacing={4} fz="sm">
            <Table.Thead>
                <Table.Tr>
                    <Table.Th>Kat.</Table.Th>
                    <Table.Th className="num">Gesamtkosten</Table.Th>
                    <Table.Th className="num">zwf. Kosten</Table.Th>
                    <Table.Th className="num">Finanzhilfen</Table.Th>
                    {!informational && periods.map((p) => <Table.Th key={p.label} className="num">{p.label}</Table.Th>)}
                </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
                {entry.amounts.map((a, i) => (
                    <Table.Tr key={`${a.category}-${i}`} fw={a.category === "SUM" ? 600 : undefined}>
                        <Table.Td>
                            {CATEGORY_LABEL[a.category] ?? a.category}
                            {a.computed && (
                                <Text span size="xs" c="dimmed" title="Im PDF ohne ∑-Zeile; aus den Kategorien berechnet">
                                    {" "}(ber.)
                                </Text>
                            )}
                        </Table.Td>
                        <Table.Td className="num">{formatMio(a.cost_total)}</Table.Td>
                        <Table.Td className="num">{formatMio(a.cost_eligible)}</Table.Td>
                        <Table.Td className="num">{formatMio(a.aid_total)}</Table.Td>
                        {!informational &&
                            periods.map((p) => (
                                <Table.Td key={p.label} className="num">
                                    {a.periods[p.label] != null ? formatMio(a.periods[p.label]) : ""}
                                </Table.Td>
                            ))}
                    </Table.Tr>
                ))}
            </Table.Tbody>
        </ResponsiveTable>
    );
}

function PeriodChart({ entry }: { entry: GvfgProjectEntry }) {
    const line = sumLine(entry);
    if (!line) return null;
    // Paid and planned years in separate (stacked) series so they differ in colour.
    const data = entry.program.periods
        .map((p) => {
            const aid = num(line.periods[p.label]) ?? 0;
            return { period: p.label, paid: p.kind === "ausgezahlt" ? aid : 0, planned: p.kind === "ausgezahlt" ? 0 : aid };
        })
        .filter((d) => d.paid !== 0 || d.planned !== 0);
    if (data.length === 0) return null;
    return (
        <BarChart
            h={200}
            data={data}
            dataKey="period"
            type="stacked"
            series={[
                { name: "paid", label: "ausgezahlt", color: CHART_SERIES[0] },
                { name: "planned", label: "geplant / Rest", color: CHART_SERIES[1] },
            ]}
            valueFormatter={(v) => formatMio(v)}
            withLegend
            tickLine="y"
        />
    );
}

function EditionHistory({ editions }: { editions: GvfgProjectEntry[] }) {
    if (editions.length < 2) return null;
    return (
        <ResponsiveTable minWidth={420} verticalSpacing={4} fz="sm">
            <Table.Thead>
                <Table.Tr>
                    <Table.Th>Ausgabe</Table.Th>
                    <Table.Th className="num">Gesamtkosten</Table.Th>
                    <Table.Th className="num">Finanzhilfen</Table.Th>
                    <Table.Th>Inbetriebnahme gepl.</Table.Th>
                </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
                {editions.map((e) => (
                    <Table.Tr key={e.id}>
                        <Table.Td>
                            {editionLabel(e.program)}
                            {e.part === "nachrichtlich" ? " (nachr.)" : ""}
                        </Table.Td>
                        <Table.Td className="num">{formatMio(sumLine(e)?.cost_total)}</Table.Td>
                        <Table.Td className="num">{formatMio(sumLine(e)?.aid_total)}</Table.Td>
                        <Table.Td>{e.commissioning_planned ?? "–"}</Table.Td>
                    </Table.Tr>
                ))}
            </Table.Tbody>
        </ResponsiveTable>
    );
}

function EntryCard({ editions }: { editions: GvfgProjectEntry[] }) {
    const [open, setOpen] = useState(false);
    const entry = editions[0];
    const total = sumLine(entry);
    return (
        <Paper withBorder p="var(--card-pad)">
            <Stack gap="sm">
                <Group justify="space-between" align="flex-start" wrap="wrap">
                    <Stack gap={4}>
                        <Group gap="xs">
                            <Badge variant="outline">{entry.key}</Badge>
                            <Badge variant="outline">Ausgabe {editionLabel(entry.program)}</Badge>
                            {entry.part === "nachrichtlich" && <Badge variant="outline">nachrichtlich</Badge>}
                        </Group>
                        <Text size="sm" fw={500}>{entry.name ?? "–"}</Text>
                        <Text size="xs" c="dimmed">
                            {[entry.land, KIND_LABEL[entry.kind] ?? entry.kind, entry.city].filter(Boolean).join(" · ")}
                        </Text>
                    </Stack>
                    <Group gap="xl">
                        <Fact label="Gesamtkosten (Mio. €)" value={formatMio(total?.cost_total)} />
                        <Fact label="Finanzhilfen (Mio. €)" value={formatMio(total?.aid_total)} />
                        <Text
                            size="xs"
                            c="blue"
                            style={{ display: "inline-flex", alignItems: "center", gap: 4, cursor: "pointer", userSelect: "none" }}
                            onClick={() => setOpen((o) => !o)}
                        >
                            {open ? "Ausblenden" : "Details"}
                            {open ? <ChevronUp size={16} aria-hidden /> : <ChevronDown size={16} aria-hidden />}
                        </Text>
                    </Group>
                </Group>
                <Group gap="xl" wrap="wrap">
                    <Fact label="Fördertatbestand" value={entry.funding_type} />
                    <Fact label="Fördersatz" value={entry.funding_rate != null ? `${entry.funding_rate} %` : null} />
                    <Fact label="Lph" value={entry.lph} />
                    <Fact label="Beginn Mittelabfluss" value={entry.start_year} />
                    <Fact label="Baubeginn" value={entry.construction_start} />
                    <Fact label="Inbetriebnahme gepl." value={entry.commissioning_planned} />
                    <Fact label="Inbetriebnahme tats." value={entry.commissioning_actual} />
                </Group>
                <Collapse in={open}>
                    <Stack gap="md" pt="xs">
                        <AmountTable entry={entry} />
                        {entry.part === "finanzrelevant" && <PeriodChart entry={entry} />}
                        {editions.length > 1 && (
                            <Stack gap={4}>
                                <Text size="sm" fw={600}>Entwicklung über die Ausgaben</Text>
                                <EditionHistory editions={editions} />
                            </Stack>
                        )}
                    </Stack>
                </Collapse>
            </Stack>
        </Paper>
    );
}

function SubprojectEntries({ groups, projectId }: { groups: GvfgProjectEntry[][]; projectId: number }) {
    return (
        <Stack gap="xs">
            <Text size="sm" fw={600}>GVFG-Förderung in Teilprojekten</Text>
            <ResponsiveTable minWidth={560} striped verticalSpacing={4} fz="sm">
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th>Teilprojekt</Table.Th>
                        <Table.Th>Schlüssel</Table.Th>
                        <Table.Th>Ausgabe</Table.Th>
                        <Table.Th className="num">Finanzhilfen (Mio. €)</Table.Th>
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    {groups.map(([entry]) => (
                        <Table.Tr key={entry.id}>
                            <Table.Td>
                                <Stack gap={0}>
                                    {entry.projects
                                        .filter((p) => p.id !== projectId)
                                        .map((p) => (
                                            <ProjectHoverCard key={p.id} projectId={p.id}>
                                                <Anchor component={Link} to={`/projects/${p.id}`} size="sm">
                                                    {p.name}
                                                </Anchor>
                                            </ProjectHoverCard>
                                        ))}
                                </Stack>
                            </Table.Td>
                            <Table.Td style={{ whiteSpace: "nowrap" }}>{entry.key}</Table.Td>
                            <Table.Td>{editionLabel(entry.program)}</Table.Td>
                            <Table.Td className="num">{formatMio(sumLine(entry)?.aid_total)}</Table.Td>
                        </Table.Tr>
                    ))}
                </Table.Tbody>
            </ResponsiveTable>
        </Stack>
    );
}

export default function GvfgSection({ projectId }: { projectId: number }) {
    const { data: entries, isLoading } = useProjectGvfg(projectId);

    if (isLoading) return <LoadingState rows={3} />;
    if (!entries || entries.length === 0) return null;

    const own = byKey(entries.filter((e) => e.projects.some((p) => p.id === projectId)));
    const children = byKey(entries.filter((e) => !e.projects.some((p) => p.id === projectId)));

    return (
        <Paper withBorder p="var(--card-pad)">
            <Stack gap="md">
                <Group className="idt-section-head" justify="space-between" wrap="wrap">
                    <Title order={2} className="idt-title-plain">GVFG-Bundesprogramm</Title>
                    <Anchor component={Link} to="/finanzen/gvfg" size="sm">Alle GVFG-Vorhaben →</Anchor>
                </Group>
                {own.map((editions) => (
                    <EntryCard key={editions[0].key} editions={editions} />
                ))}
                {children.length > 0 && <SubprojectEntries groups={children} projectId={projectId} />}
                <Text size="xs" c="dimmed">
                    Beträge in Mio. €. {CATEGORY_LABEL.A}: endgültig, {CATEGORY_LABEL.B}: vorläufig,{" "}
                    {CATEGORY_LABEL.C}: bedingt aufgenommen.
                </Text>
            </Stack>
        </Paper>
    );
}
