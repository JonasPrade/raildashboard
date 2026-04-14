import { useState } from "react";
import {
    Box,
    Collapse,
    ColorSwatch,
    Group,
    Loader,
    Stack,
    Table,
    Tabs,
    Text,
    Title,
} from "@mantine/core";
import { ChronicleCard, ChronicleDataChip } from "../../../components/chronicle";
import { DonutChart, LineChart } from "@mantine/charts";
import {
    type FinveWithBudgets,
    type BudgetSummary,
    type TitelEntry,
    useProjectFinves,
} from "../../../shared/api/queries";

function fmt(val: number | null) {
    if (val === null || val === 0) return "–";
    return val.toLocaleString("de-DE") + " T€";
}

function fmtNum(val: number | null): number {
    return val ?? 0;
}

// ---------------------------------------------------------------------------
// Collect all unique non-nachrichtlich titeln across all budget years
// Returns { key: short chart key, label: full readable label }
// ---------------------------------------------------------------------------

// Distinct CSS hex colors for up to 10 Titel series (must be plain CSS for DonutChart)
const SERIE_COLORS = [
    "#339af0", "#20c997", "#51cf66", "#fcc419", "#ff922b",
    "#ff6b6b", "#cc5de8", "#5c7cfa", "#22b8cf", "#94d82d",
];

// ---------------------------------------------------------------------------
// DonutChart: veranschlagt per Haushaltstiteln for the most recent report
// ---------------------------------------------------------------------------

function buildPieData(budget: BudgetSummary) {
    return budget.titel_entries
        .filter((e) => !e.is_nachrichtlich && (e.veranschlagt ?? 0) > 0)
        .map((e, i) => ({
            name: e.label,
            value: e.veranschlagt ?? 0,
            color: SERIE_COLORS[i % SERIE_COLORS.length],
        }));
}

// ---------------------------------------------------------------------------
// Custom legend rendered below a chart (avoids recharts clipping issues)
// ---------------------------------------------------------------------------

function ChartLegend({ items }: { items: { label: string; color: string }[] }) {
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

// ---------------------------------------------------------------------------
// LineChart: total cost estimate per report year (one series)
// ---------------------------------------------------------------------------

function buildLineData(budgets: BudgetSummary[]) {
    return budgets.map((b) => ({
        Jahr: String(b.budget_year),
        "Gesamtkosten": fmtNum(b.cost_estimate_actual),
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

function fmtChart(v: number | null) {
    return v != null ? v.toLocaleString("de-DE") + " T€" : "–";
}

// ---------------------------------------------------------------------------
// Titel detail table per year
// ---------------------------------------------------------------------------

function TitelTable({ entries, year }: { entries: TitelEntry[]; year: number }) {
    const regular = entries.filter((e) => !e.is_nachrichtlich);
    const nachrichtlich = entries.filter((e) => e.is_nachrichtlich);

    const renderRows = (rows: TitelEntry[]) =>
        rows.map((e, i) => (
            <Table.Tr key={i}>
                <Table.Td><Text size="xs">{e.label}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs">{fmt(e.cost_estimate_last_year)}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs">{fmt(e.cost_estimate_aktuell)}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs">{fmt(e.verausgabt_bis)}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs">{fmt(e.bewilligt)}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs">{fmt(e.ausgabereste_transferred)}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs" fw={600}>{fmt(e.veranschlagt)}</Text></Table.Td>
                <Table.Td ta="right"><Text size="xs">{fmt(e.vorhalten_future)}</Text></Table.Td>
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

// ---------------------------------------------------------------------------
// Single FinVe card with charts
// ---------------------------------------------------------------------------

function FinveCard({ finve }: { finve: FinveWithBudgets }) {
    const [open, setOpen] = useState(false);
    const hasBudgets = finve.budgets.length > 0;
    const hasMultipleYears = finve.budgets.length >= 2;
    const lastBudget = finve.budgets.at(-1);
    const hasTitelEntries = (lastBudget?.titel_entries ?? []).some(
        (e) => !e.is_nachrichtlich && (e.veranschlagt ?? 0) > 0
    );

    const pieData = lastBudget ? buildPieData(lastBudget) : [];
    const lineData = buildLineData(finve.budgets);
    const yMax = Math.ceil(
        Math.max(...finve.budgets.map((b) => b.cost_estimate_actual ?? 0)) * 1.1
    );

    const firstTab = hasMultipleYears ? "costs" : hasTitelEntries ? "budget" : "table";

    // SammelFinVe: show compact tag only
    if (finve.is_sammel_finve) {
        return (
            <Group gap="xs" align="center">
                <ChronicleDataChip>Sammel-FinVe</ChronicleDataChip>
                <ChronicleDataChip>FinVe {finve.id}</ChronicleDataChip>
                <Text size="sm" c="dimmed">{finve.name ?? "–"}</Text>
            </Group>
        );
    }

    return (
        <ChronicleCard>
            <Stack gap="sm">
                <Group justify="space-between" align="flex-start" wrap="wrap">
                    <Group gap="sm" align="center">
                        <ChronicleDataChip>FinVe {finve.id}</ChronicleDataChip>
                        <Text size="sm" fw={500}>{finve.name ?? "–"}</Text>
                    </Group>
                    <Group gap="xl">
                        {finve.starting_year && (
                            <Stack gap={0} align="flex-end">
                                <Text size="xs" c="dimmed">Aufnahme</Text>
                                <Text size="sm" fw={500}>{finve.starting_year}</Text>
                            </Stack>
                        )}
                        {finve.cost_estimate_original != null && (
                            <Stack gap={0} align="flex-end">
                                <Text size="xs" c="dimmed">Ursprgl. Kosten</Text>
                                <Text size="sm" fw={500}>{fmt(finve.cost_estimate_original)}</Text>
                            </Stack>
                        )}
                        {lastBudget?.cost_estimate_actual != null && (
                            <Stack gap={0} align="flex-end">
                                <Text size="xs" c="dimmed">Aktuelle Kosten ({lastBudget.budget_year})</Text>
                                <Text size="sm" fw={500}>{fmt(lastBudget.cost_estimate_actual)}</Text>
                            </Stack>
                        )}
                        {hasBudgets && (
                            <Text
                                size="xs"
                                c="blue"
                                style={{ cursor: "pointer", userSelect: "none" }}
                                onClick={() => setOpen((o) => !o)}
                            >
                                {open ? "Ausblenden ▲" : "Details & Diagramme ▼"}
                            </Text>
                        )}
                    </Group>
                </Group>

                {hasBudgets && (
                    <Collapse in={open}>
                        <Tabs defaultValue={firstTab} mt="xs">
                            <Tabs.List>
                                {hasMultipleYears && (
                                    <Tabs.Tab value="costs">Kostenentwicklung</Tabs.Tab>
                                )}
                                {hasTitelEntries && (
                                    <Tabs.Tab value="budget">Budgetverteilung</Tabs.Tab>
                                )}
                                {lastBudget && lastBudget.titel_entries.length > 0 && (
                                    <Tabs.Tab value="table">Haushaltbericht {lastBudget!.budget_year}</Tabs.Tab>
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
                                                valueFormatter={fmtChart}
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
                                                valueFormatter={(v) => v.toLocaleString("de-DE") + " T€"}
                                            />
                                        </Group>
                                        <ChartLegend
                                            items={pieData.map((d) => ({
                                                label: d.name,
                                                color: d.color,
                                            }))}
                                        />
                                    </Stack>
                                </Tabs.Panel>
                            )}

                            {/* Detail table for the most recent year */}
                            {lastBudget && lastBudget.titel_entries.length > 0 && (
                                <Tabs.Panel value="table" pt="md">
                                    <TitelTable
                                        entries={lastBudget.titel_entries}
                                        year={lastBudget.budget_year}
                                    />
                                </Tabs.Panel>
                            )}
                        </Tabs>
                    </Collapse>
                )}
            </Stack>
        </ChronicleCard>
    );
}

// ---------------------------------------------------------------------------
// Public section component
// ---------------------------------------------------------------------------

export default function FinveSection({ projectId }: { projectId: number }) {
    const { data: finves, isLoading } = useProjectFinves(projectId);

    if (isLoading) return <Loader size="sm" />;
    if (!finves || finves.length === 0) return null;

    return (
        <ChronicleCard>
            <Stack gap="md">
                <Title order={4}>Finanzierungsvereinbarungen (FinVe)</Title>
                {finves.map((finve) => (
                    <FinveCard key={finve.id} finve={finve} />
                ))}
            </Stack>
        </ChronicleCard>
    );
}
