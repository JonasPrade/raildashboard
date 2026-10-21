/**
 * Shared FinVe budget visualisation: chart builders, legend, the per-year
 * Titel table and the Tabs block (Kostenentwicklung / Budgetverteilung /
 * Haushaltbericht). Used by the project detail (FinveSection) and the FinVe
 * overview page — both keep their own card headers and collapse toggles.
 */

import { Box, Group, Stack, Table, Tabs, Text, type MantineSpacing } from "@mantine/core";
import { ResponsiveTable } from "../../../shared/ui/ResponsiveTable";
import { DonutChart, LineChart } from "@mantine/charts";
import "@mantine/charts/styles.css";
import "../../../shared/ui/charts.css";

import type { BudgetSummary, TitelEntry } from "../../../shared/api/queries";
import { useIsMobile } from "../../../shared/hooks/useBreakpoint";
import { CHART_SERIES, CHART_SERIES_OVERFLOW } from "../../../shared/theme/semanticColors";
import { chartNum, formatTEuro, formatTEuroWithZero } from "../../../shared/format";

/** Colour of the i-th series: the six chart colours, everything beyond in the overflow colour. */
export function seriesColor(i: number): string {
    return i < CHART_SERIES.length ? CHART_SERIES[i] : CHART_SERIES_OVERFLOW;
}

export function buildPieData(budget: BudgetSummary) {
    return budget.titel_entries
        .filter((e) => !e.is_nachrichtlich && (e.veranschlagt ?? 0) > 0)
        .map((e, i) => ({
            name: e.label,
            value: e.veranschlagt ?? 0,
            color: seriesColor(i),
        }));
}

/** Legend entries: the first six series by name, all further ones grouped as "weitere". */
export function buildLegendItems(data: { name: string; color: string }[]): { label: string; color: string }[] {
    const head = data.slice(0, CHART_SERIES.length).map((d) => ({ label: d.name, color: d.color }));
    const rest = data.length - CHART_SERIES.length;
    return rest > 0 ? [...head, { label: `weitere (${rest})`, color: CHART_SERIES_OVERFLOW }] : head;
}

export function buildLineData(budgets: BudgetSummary[]) {
    return budgets.map((b) => ({
        Jahr: String(b.budget_year),
        "Gesamtkosten": chartNum(b.cost_estimate_actual),
    }));
}

// Custom legend rendered below a chart (avoids recharts clipping issues)
export function ChartLegend({ items }: { items: { label: string; color: string }[] }) {
    return (
        <div className="idt-chart-legend">
            {items.map((item) => (
                <span key={item.label} className="idt-chart-legend__item">
                    <span className="idt-chart-legend__swatch" style={{ background: item.color }} aria-hidden />
                    {item.label}
                </span>
            ))}
        </div>
    );
}

// Titel detail table per year (8-column head, regular + nachrichtlich blocks)
export function TitelTable({ entries, year }: { entries: TitelEntry[]; year: number }) {
    const regular = entries.filter((e) => !e.is_nachrichtlich);
    const nachrichtlich = entries.filter((e) => e.is_nachrichtlich);

    const renderRows = (rows: TitelEntry[]) =>
        rows.map((e, i) => (
            <Table.Tr key={i}>
                <Table.Td><Text size="xs">{e.label}</Text></Table.Td>
                <Table.Td className="num"><Text size="xs">{formatTEuro(e.cost_estimate_last_year)}</Text></Table.Td>
                <Table.Td className="num"><Text size="xs">{formatTEuro(e.cost_estimate_aktuell)}</Text></Table.Td>
                <Table.Td className="num"><Text size="xs">{formatTEuro(e.verausgabt_bis)}</Text></Table.Td>
                <Table.Td className="num"><Text size="xs">{formatTEuro(e.bewilligt)}</Text></Table.Td>
                <Table.Td className="num"><Text size="xs">{formatTEuro(e.ausgabereste_transferred)}</Text></Table.Td>
                <Table.Td className="num"><Text size="xs" fw={600}>{formatTEuro(e.veranschlagt)}</Text></Table.Td>
                <Table.Td className="num"><Text size="xs">{formatTEuro(e.vorhalten_future)}</Text></Table.Td>
            </Table.Tr>
        ));

    const thead = (
        <Table.Thead>
            <Table.Tr>
                <Table.Th>Kapitel / Titel</Table.Th>
                <Table.Th className="num">Vorjahr</Table.Th>
                <Table.Th className="num">Aktuell</Table.Th>
                <Table.Th className="num">Verausgabt bis {year - 1}</Table.Th>
                <Table.Th className="num">Bewilligt {year}</Table.Th>
                <Table.Th className="num">Ausgabereste</Table.Th>
                <Table.Th className="num">Veranschlagt {year}</Table.Th>
                <Table.Th className="num">Vorhalten {year + 1} ff.</Table.Th>
            </Table.Tr>
        </Table.Thead>
    );

    return (
        <Stack gap="xs">
            {regular.length > 0 && (
                <ResponsiveTable minWidth={800} withColumnBorders fz="xs">
                    {thead}
                    <Table.Tbody>{renderRows(regular)}</Table.Tbody>
                </ResponsiveTable>
            )}
            {nachrichtlich.length > 0 && (
                <Stack gap={4}>
                    <Text size="xs" fw={600} c="dimmed">Nachrichtlich: EVU / Dritte</Text>
                    <ResponsiveTable minWidth={800} withColumnBorders fz="xs">
                        {thead}
                        <Table.Tbody>{renderRows(nachrichtlich)}</Table.Tbody>
                    </ResponsiveTable>
                </Stack>
            )}
        </Stack>
    );
}

/** Which tab should open first, given the available data. */
export function firstBudgetTab(budgets: BudgetSummary[]): string {
    return budgets.length >= 2 ? "costs" : hasTitelChartEntries(budgets) ? "budget" : "table";
}

function hasTitelChartEntries(budgets: BudgetSummary[]): boolean {
    return (budgets.at(-1)?.titel_entries ?? []).some(
        (e) => !e.is_nachrichtlich && (e.veranschlagt ?? 0) > 0,
    );
}

/** The Tabs block with LineChart, DonutChart and Titel table for one FinVe. */
export function FinveBudgetDetails({
    budgets,
    tabsMt,
}: {
    budgets: BudgetSummary[];
    tabsMt?: MantineSpacing;
}) {
    const isMobile = useIsMobile();
    const hasMultipleYears = budgets.length >= 2;
    const lastBudget = budgets.at(-1);
    const hasTitelEntries = hasTitelChartEntries(budgets);

    const pieData = lastBudget ? buildPieData(lastBudget) : [];
    const lineData = buildLineData(budgets);
    const yMax = Math.ceil(
        Math.max(...budgets.map((b) => b.cost_estimate_actual ?? 0)) * 1.1
    );

    return (
        <Tabs defaultValue={firstBudgetTab(budgets)} mt={tabsMt}>
            <Tabs.List>
                {hasMultipleYears && (
                    <Tabs.Tab value="costs">Kostenentwicklung</Tabs.Tab>
                )}
                {hasTitelEntries && (
                    <Tabs.Tab value="budget">Budgetverteilung</Tabs.Tab>
                )}
                {lastBudget && lastBudget.titel_entries.length > 0 && (
                    <Tabs.Tab value="table">Haushaltbericht {lastBudget.budget_year}</Tabs.Tab>
                )}
            </Tabs.List>

            {/* LineChart: total cost estimate per report year */}
            {hasMultipleYears && (
                <Tabs.Panel value="costs" pt="md">
                    <Stack gap="xs">
                        <Text size="xs" c="dimmed">
                            Gesamtkostenschätzung je Haushaltsbericht (T€)
                        </Text>
                        <Box style={{ overflowX: "auto" }}>
                            <LineChart
                                h={280}
                                data={lineData}
                                dataKey="Jahr"
                                series={[{ name: "Gesamtkosten", color: CHART_SERIES[0] }]}
                                curveType="monotone"
                                tickLine="x"
                                gridAxis="y"
                                withDots
                                valueFormatter={formatTEuroWithZero}
                                // A 130px axis would leave almost no plot area on a phone.
                                yAxisProps={{ width: isMobile ? 64 : 130, domain: [0, yMax] }}
                            />
                        </Box>
                    </Stack>
                </Tabs.Panel>
            )}

            {/* DonutChart: veranschlagt per Titel for the most recent report */}
            {hasTitelEntries && (
                <Tabs.Panel value="budget" pt="md">
                    <Stack gap="xs">
                        <Text size="xs" c="dimmed">
                            Budgetverteilung nach Haushaltstiteln – Haushaltsbericht {lastBudget!.budget_year} (T€)
                        </Text>
                        <Group justify="center">
                            <DonutChart
                                data={pieData}
                                size={isMobile ? 170 : 220}
                                thickness={isMobile ? 28 : 36}
                                withTooltip
                                tooltipDataSource="segment"
                                valueFormatter={formatTEuroWithZero}
                            />
                        </Group>
                        <ChartLegend
                            items={buildLegendItems(pieData)}
                        />
                    </Stack>
                </Tabs.Panel>
            )}

            {/* Detail table for the most recent year */}
            {lastBudget && lastBudget.titel_entries.length > 0 && (
                <Tabs.Panel value="table" pt="md">
                    <TitelTable entries={lastBudget.titel_entries} year={lastBudget.budget_year} />
                </Tabs.Panel>
            )}
        </Tabs>
    );
}
