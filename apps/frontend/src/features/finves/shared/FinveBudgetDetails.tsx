/**
 * Shared FinVe budget visualisation: chart builders, legend, the per-year
 * Titel table and the Tabs block (Kostenentwicklung / Budgetverteilung /
 * Haushaltbericht). Used by the project detail (FinveSection) and the FinVe
 * overview page — both keep their own card headers and collapse toggles.
 */

import { Box, ColorSwatch, Group, Stack, Table, Tabs, Text, type MantineSpacing } from "@mantine/core";
import { DonutChart, LineChart } from "@mantine/charts";

import type { BudgetSummary, TitelEntry } from "../../../shared/api/queries";
import { chartNum, formatTEuro, formatTEuroWithZero } from "../../../shared/format";

// Distinct CSS hex colors for up to 10 Titel series (must be plain CSS for DonutChart)
const SERIE_COLORS = [
    "#339af0", "#20c997", "#51cf66", "#fcc419", "#ff922b",
    "#ff6b6b", "#cc5de8", "#5c7cfa", "#22b8cf", "#94d82d",
];

export function buildPieData(budget: BudgetSummary) {
    return budget.titel_entries
        .filter((e) => !e.is_nachrichtlich && (e.veranschlagt ?? 0) > 0)
        .map((e, i) => ({
            name: e.label,
            value: e.veranschlagt ?? 0,
            color: SERIE_COLORS[i % SERIE_COLORS.length],
        }));
}

export function buildLineData(budgets: BudgetSummary[]) {
    return budgets.map((b) => ({
        Jahr: String(b.budget_year),
        "Gesamtkosten": chartNum(b.cost_estimate_actual),
    }));
}

const CHART_TOOLTIP_PROPS = {
    contentStyle: {
        background: "var(--mantine-color-body)",
        border: "1px solid var(--mantine-color-default-border)",
        borderRadius: "var(--mantine-radius-sm)",
        color: "var(--mantine-color-text)",
        fontSize: 12,
    },
} as const;

// Custom legend rendered below a chart (avoids recharts clipping issues)
export function ChartLegend({ items }: { items: { label: string; color: string }[] }) {
    return (
        <Group gap="md" mt="xs" wrap="wrap">
            {items.map((item) => (
                <Group key={item.label} gap={6} align="center">
                    <ColorSwatch color={item.color} size={12} />
                    <Text size="xs" c="dimmed">{item.label}</Text>
                </Group>
            ))}
        </Group>
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
                <Table.Td ta="right"><Text size="xs">{formatTEuro(e.cost_estimate_last_year)}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs">{formatTEuro(e.cost_estimate_aktuell)}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs">{formatTEuro(e.verausgabt_bis)}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs">{formatTEuro(e.bewilligt)}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs">{formatTEuro(e.ausgabereste_transferred)}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs" fw={600}>{formatTEuro(e.veranschlagt)}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs">{formatTEuro(e.vorhalten_future)}</Text></Table.Td>
            </Table.Tr>
        ));

    const thead = (
        <Table.Thead>
            <Table.Tr>
                <Table.Th>Kapitel / Titel</Table.Th>
                <Table.Th ta="right">Vorjahr</Table.Th>
                <Table.Th ta="right">Aktuell</Table.Th>
                <Table.Th ta="right">Verausgabt bis {year - 1}</Table.Th>
                <Table.Th ta="right">Bewilligt {year}</Table.Th>
                <Table.Th ta="right">Ausgabereste</Table.Th>
                <Table.Th ta="right">Veranschlagt {year}</Table.Th>
                <Table.Th ta="right">Vorhalten {year + 1} ff.</Table.Th>
            </Table.Tr>
        </Table.Thead>
    );

    return (
        <Stack gap="xs">
            {regular.length > 0 && (
                <Box style={{ overflowX: "auto" }}>
                    <Table withColumnBorders fz="xs" style={{ minWidth: 800 }}>
                        {thead}
                        <Table.Tbody>{renderRows(regular)}</Table.Tbody>
                    </Table>
                </Box>
            )}
            {nachrichtlich.length > 0 && (
                <Stack gap={4}>
                    <Text size="xs" fw={600} c="dimmed">Nachrichtlich: EVU / Dritte</Text>
                    <Box style={{ overflowX: "auto" }}>
                        <Table withColumnBorders fz="xs" style={{ minWidth: 800 }}>
                            {thead}
                            <Table.Tbody>{renderRows(nachrichtlich)}</Table.Tbody>
                        </Table>
                    </Box>
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
                                series={[{ name: "Gesamtkosten", color: "green.6" }]}
                                curveType="monotone"
                                tickLine="x"
                                gridAxis="y"
                                withDots
                                valueFormatter={formatTEuroWithZero}
                                yAxisProps={{ width: 130, domain: [0, yMax] }}
                                tooltipProps={CHART_TOOLTIP_PROPS}
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
                                size={220}
                                thickness={36}
                                withTooltip
                                tooltipDataSource="segment"
                                valueFormatter={formatTEuroWithZero}
                            />
                        </Group>
                        <ChartLegend
                            items={pieData.map((d) => ({ label: d.name, color: d.color }))}
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
