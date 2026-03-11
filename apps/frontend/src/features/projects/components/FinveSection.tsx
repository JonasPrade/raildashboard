import { useState } from "react";
import {
    Badge,
    Box,
    Card,
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
import { BarChart, LineChart } from "@mantine/charts";
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

type TitelMeta = { key: string; label: string; color: string };

function collectTitelMeta(budgets: BudgetSummary[]): TitelMeta[] {
    const seen = new Map<string, string>(); // titel_key → full label
    for (const b of budgets) {
        for (const e of b.titel_entries) {
            if (!e.is_nachrichtlich && !seen.has(e.titel_key)) {
                seen.set(e.titel_key, e.label);
            }
        }
    }
    return [...seen.entries()].map(([key, label], i) => ({
        // Short key used as recharts dataKey (must be unique, no spaces issues)
        key: `Kap. ${key.split("_")[0]} · ${key.split("_").slice(1).join(" ")}`,
        label,
        color: SERIE_COLORS[i % SERIE_COLORS.length],
    }));
}

// Distinct colors for up to 10 Titel series
const SERIE_COLORS = [
    "blue.5", "teal.5", "green.5", "yellow.5", "orange.5",
    "red.5", "grape.5", "indigo.5", "cyan.5", "lime.5",
];

// ---------------------------------------------------------------------------
// BarChart: veranschlagt per Haushaltstiteln, stacked, per year
// ---------------------------------------------------------------------------

function buildTitelBarData(budgets: BudgetSummary[], metas: TitelMeta[]) {
    return budgets.map((b) => {
        const row: Record<string, string | number> = { Jahr: String(b.budget_year) };
        for (const meta of metas) {
            // match by titel_key reconstructed from meta.key
            const entry = b.titel_entries.find(
                (e) => !e.is_nachrichtlich &&
                    `Kap. ${e.titel_key.split("_")[0]} · ${e.titel_key.split("_").slice(1).join(" ")}` === meta.key
            );
            row[meta.key] = fmtNum(entry?.veranschlagt ?? null);
        }
        return row;
    });
}

// ---------------------------------------------------------------------------
// Custom legend rendered below a chart (avoids recharts clipping issues)
// ---------------------------------------------------------------------------

function ChartLegend({ items }: { items: { label: string; color: string }[] }) {
    return (
        <Group gap="md" mt="xs" wrap="wrap">
            {items.map((item) => (
                <Group key={item.label} gap={6} align="center">
                    <ColorSwatch color={`var(--mantine-color-${item.color.replace(".", "-")})`} size={12} />
                    <Text size="xs" c="dimmed">{item.label}</Text>
                </Group>
            ))}
        </Group>
    );
}

// ---------------------------------------------------------------------------
// LineChart: cost estimate trend over years
// ---------------------------------------------------------------------------

function buildLineData(budgets: BudgetSummary[]) {
    return budgets.map((b) => ({
        Jahr: String(b.budget_year),
        "Ursprünglich": fmtNum(b.cost_estimate_original),
        "Vorjahr": fmtNum(b.cost_estimate_last_year),
        "Aktuell": fmtNum(b.cost_estimate_actual),
    }));
}

const LINE_SERIES = [
    { name: "Ursprünglich", color: "gray.5", strokeDasharray: "5 5" },
    { name: "Vorjahr", color: "blue.4" },
    { name: "Aktuell", color: "green.6" },
] as const;

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
    const hasTitelEntries = finve.budgets.some((b) => b.titel_entries.length > 0);

    const titelMetas = collectTitelMeta(finve.budgets);
    const barSeries = titelMetas.map((m) => ({ name: m.key, color: m.color }));
    const barData = buildTitelBarData(finve.budgets, titelMetas);
    const lineData = buildLineData(finve.budgets);

    const firstTab = hasTitelEntries ? "budget" : hasMultipleYears ? "costs" : "table";

    // Last budget year for the table tab
    const lastBudget = finve.budgets.at(-1);

    // SammelFinVe: show compact tag only
    if (finve.is_sammel_finve) {
        return (
            <Group gap="xs" align="center">
                <Badge variant="light" color="orange" size="md">
                    Sammel-FinVe
                </Badge>
                <Badge variant="outline" color="indigo" size="md">
                    FinVe {finve.id}
                </Badge>
                <Text size="sm" c="dimmed">{finve.name ?? "–"}</Text>
            </Group>
        );
    }

    return (
        <Card withBorder radius="md" padding="md" shadow="xs">
            <Stack gap="sm">
                <Group justify="space-between" align="flex-start" wrap="wrap">
                    <Group gap="sm" align="center">
                        <Badge variant="light" color="indigo" size="md">
                            FinVe {finve.id}
                        </Badge>
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
                                {hasTitelEntries && (
                                    <Tabs.Tab value="budget">Budgetverteilung</Tabs.Tab>
                                )}
                                {hasMultipleYears && (
                                    <Tabs.Tab value="costs">Kostenentwicklung</Tabs.Tab>
                                )}
                                {lastBudget && lastBudget.titel_entries.length > 0 && (
                                    <Tabs.Tab value="table">
                                        Haushaltstiteln {lastBudget.budget_year}
                                    </Tabs.Tab>
                                )}
                            </Tabs.List>

                            {/* Stacked BarChart: veranschlagt per Titel per year */}
                            {hasTitelEntries && (
                                <Tabs.Panel value="budget" pt="md">
                                    <Stack gap="xs">
                                        <Text size="xs" c="dimmed">
                                            Veranschlagte Mittel je Haushaltstiteln und Jahr (T€)
                                        </Text>
                                        <Box style={{ overflowX: "auto" }}>
                                            <BarChart
                                                h={280}
                                                data={barData}
                                                dataKey="Jahr"
                                                series={barSeries}
                                                type="stacked"
                                                tickLine="x"
                                                gridAxis="y"
                                                valueFormatter={(v) =>
                                                    v != null ? v.toLocaleString("de-DE") + " T€" : "–"
                                                }
                                                tooltipProps={{
                                                    contentStyle: {
                                                        background: "var(--mantine-color-body)",
                                                        border: "1px solid var(--mantine-color-default-border)",
                                                        borderRadius: "var(--mantine-radius-sm)",
                                                        color: "var(--mantine-color-text)",
                                                        fontSize: 12,
                                                    },
                                                }}
                                            />
                                        </Box>
                                        <ChartLegend
                                            items={titelMetas.map((m) => ({
                                                label: m.label,
                                                color: m.color,
                                            }))}
                                        />
                                    </Stack>
                                </Tabs.Panel>
                            )}

                            {/* LineChart: cost estimate trend — only with ≥ 2 budget years */}
                            {hasMultipleYears && (
                                <Tabs.Panel value="costs" pt="md">
                                    <Stack gap="xs">
                                        <Text size="xs" c="dimmed">
                                            Entwicklung der Gesamtkostenschätzung über die Jahre (T€)
                                        </Text>
                                        <Box style={{ overflowX: "auto" }}>
                                            <LineChart
                                                h={280}
                                                data={lineData}
                                                dataKey="Jahr"
                                                series={LINE_SERIES.map((s) => ({
                                                    name: s.name,
                                                    color: s.color,
                                                    strokeDasharray:
                                                        "strokeDasharray" in s
                                                            ? s.strokeDasharray
                                                            : undefined,
                                                }))}
                                                curveType="monotone"
                                                tickLine="x"
                                                gridAxis="y"
                                                withDots
                                                valueFormatter={(v) =>
                                                    v != null ? v.toLocaleString("de-DE") + " T€" : "–"
                                                }
                                                tooltipProps={{
                                                    contentStyle: {
                                                        background: "var(--mantine-color-body)",
                                                        border: "1px solid var(--mantine-color-default-border)",
                                                        borderRadius: "var(--mantine-radius-sm)",
                                                        color: "var(--mantine-color-text)",
                                                        fontSize: 12,
                                                    },
                                                }}
                                            />
                                        </Box>
                                        <ChartLegend
                                            items={LINE_SERIES.map((s) => ({
                                                label: s.name,
                                                color: s.color,
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
        </Card>
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
        <Card withBorder radius="md" padding="lg" shadow="xs">
            <Stack gap="md">
                <Title order={4}>Finanzierungsvereinbarungen (FinVe)</Title>
                {finves.map((finve) => (
                    <FinveCard key={finve.id} finve={finve} />
                ))}
            </Stack>
        </Card>
    );
}
