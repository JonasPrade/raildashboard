import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
    Alert,
    Badge,
    Box,
    Card,
    Collapse,
    ColorSwatch,
    Container,
    Group,
    Loader,
    Paper,
    SegmentedControl,
    Stack,
    Table,
    Tabs,
    Text,
    TextInput,
    Title,
    UnstyledButton,
} from "@mantine/core";
import { DonutChart, LineChart } from "@mantine/charts";
import { useFinves, type BudgetSummary, type FinveListItem, type TitelEntry } from "../../shared/api/queries";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type TypeFilter = "all" | "regular" | "sammel";

function fmt(val: number | null) {
    if (val === null || val === 0) return "–";
    return val.toLocaleString("de-DE") + " T€";
}

function fmtNum(val: number | null): number {
    return val ?? 0;
}

// ---------------------------------------------------------------------------
// Chart data builders (same logic as FinveSection.tsx)
// ---------------------------------------------------------------------------

// Distinct CSS hex colors for up to 10 Titel series (must be plain CSS for DonutChart)
const SERIE_COLORS = [
    "#339af0", "#20c997", "#51cf66", "#fcc419", "#ff922b",
    "#ff6b6b", "#cc5de8", "#5c7cfa", "#22b8cf", "#94d82d",
];

function buildPieData(budget: BudgetSummary) {
    return budget.titel_entries
        .filter((e) => !e.is_nachrichtlich && (e.veranschlagt ?? 0) > 0)
        .map((e, i) => ({
            name: e.label,
            value: e.veranschlagt ?? 0,
            color: SERIE_COLORS[i % SERIE_COLORS.length],
        }));
}

function buildLineData(budgets: BudgetSummary[]) {
    return budgets.map((b) => ({
        Jahr: String(b.budget_year),
        "Gesamtkosten": fmtNum(b.cost_estimate_actual),
    }));
}

// ---------------------------------------------------------------------------
// Chart legend
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
// Titel detail table
// ---------------------------------------------------------------------------

function TitelTable({ entries, year }: { entries: TitelEntry[]; year: number }) {
    const regular = entries.filter((e) => !e.is_nachrichtlich);
    const nachrichtlich = entries.filter((e) => e.is_nachrichtlich);

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
// Single FinVe card
// ---------------------------------------------------------------------------

function FinveCard({ finve }: { finve: FinveListItem }) {
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

    return (
        <Card withBorder radius="md" padding="lg" shadow="xs">
            <Stack gap="md">
                {/* ── Header row ─────────────────────────────────────────── */}
                <Group justify="space-between" align="flex-start" wrap="wrap" gap="sm">
                    <Stack gap={4}>
                        <Group gap="sm" align="center">
                            <Badge
                                variant="filled"
                                color={finve.is_sammel_finve ? "violet" : "blue"}
                                size="md"
                                radius="sm"
                                ff="monospace"
                            >
                                {finve.id}
                            </Badge>
                            {finve.is_sammel_finve && (
                                <Badge variant="light" color="violet" size="sm">Sammel-FinVe</Badge>
                            )}
                            {finve.temporary_finve_number && (
                                <Badge variant="outline" color="orange" size="sm">vorläufig</Badge>
                            )}
                        </Group>
                        <Text fw={600} size="md" lh={1.3}>
                            {finve.name ?? "—"}
                        </Text>
                    </Stack>

                    <Group gap="xl" align="flex-start">
                        {finve.starting_year != null && (
                            <Stack gap={2} align="flex-end">
                                <Text size="xs" c="dimmed">Aufnahme</Text>
                                <Text size="sm" fw={600}>{finve.starting_year}</Text>
                            </Stack>
                        )}
                        {finve.cost_estimate_original != null && (
                            <Stack gap={2} align="flex-end">
                                <Text size="xs" c="dimmed">Ursprgl. Kosten</Text>
                                <Text size="sm" fw={600}>{fmt(finve.cost_estimate_original)}</Text>
                            </Stack>
                        )}
                        {lastBudget?.cost_estimate_actual != null && (
                            <Stack gap={2} align="flex-end">
                                <Text size="xs" c="dimmed">Aktuell ({lastBudget.budget_year})</Text>
                                <Text size="sm" fw={600}>{fmt(lastBudget.cost_estimate_actual)}</Text>
                            </Stack>
                        )}
                    </Group>
                </Group>

                {/* ── Linked projects ────────────────────────────────────── */}
                {finve.projects.length > 0 && (
                    <Stack gap={6}>
                        <Text size="xs" c="dimmed" fw={500} tt="uppercase" style={{ letterSpacing: "0.05em" }}>
                            Verknüpfte Projekte
                        </Text>
                        <Group gap="xs" wrap="wrap">
                            {finve.projects.map((p) => (
                                <Paper
                                    key={p.id}
                                    component={Link}
                                    to={`/projects/${p.id}`}
                                    withBorder
                                    radius="sm"
                                    px="sm"
                                    py={4}
                                    style={{
                                        textDecoration: "none",
                                        cursor: "pointer",
                                        display: "inline-flex",
                                        alignItems: "center",
                                        gap: 6,
                                        transition: "background 0.15s",
                                    }}
                                    styles={{
                                        root: {
                                            "&:hover": {
                                                backgroundColor: "var(--mantine-color-blue-0)",
                                                borderColor: "var(--mantine-color-blue-4)",
                                            },
                                        },
                                    }}
                                >
                                    <Text size="xs" c="dimmed" ff="monospace">{p.id}</Text>
                                    <Text size="xs" fw={500} c="dark">{p.name}</Text>
                                </Paper>
                            ))}
                        </Group>
                    </Stack>
                )}

                {/* ── Expandable charts / budget details ─────────────────── */}
                {hasBudgets && (
                    <>
                        <UnstyledButton
                            onClick={() => setOpen((o) => !o)}
                            style={{ alignSelf: "flex-start" }}
                        >
                            <Text size="sm" c="blue" style={{ userSelect: "none" }}>
                                {open ? "▲ Diagramme ausblenden" : "▼ Details & Diagramme"}
                            </Text>
                        </UnstyledButton>

                        <Collapse in={open}>
                            <Tabs defaultValue={firstTab}>
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
                                                    valueFormatter={(v: number) => v != null ? v.toLocaleString("de-DE") + " T€" : "–"}
                                                    yAxisProps={{ width: 130, domain: [0, yMax] }}
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
                                                    valueFormatter={(v: number) => v.toLocaleString("de-DE") + " T€"}
                                                />
                                            </Group>
                                            <ChartLegend
                                                items={pieData.map((d) => ({ label: d.name, color: d.color }))}
                                            />
                                        </Stack>
                                    </Tabs.Panel>
                                )}

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
                    </>
                )}
            </Stack>
        </Card>
    );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function FinveOverviewPage() {
    const [search, setSearch] = useState("");
    const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");

    const { data: finves, isLoading, isError } = useFinves();

    const filtered = useMemo(() => {
        const q = search.trim().toLowerCase();
        return (finves ?? []).filter((f) => {
            if (typeFilter === "sammel" && !f.is_sammel_finve) return false;
            if (typeFilter === "regular" && f.is_sammel_finve) return false;
            if (q) {
                const matchesName = f.name?.toLowerCase().includes(q) ?? false;
                const matchesId = String(f.id).includes(q);
                if (!matchesName && !matchesId) return false;
            }
            return true;
        });
    }, [finves, search, typeFilter]);

    return (
        <Container size="xl" py="xl">
            <Stack gap="lg">
                <Title order={2}>Finanzierungsvereinbarungen</Title>

                <Group>
                    <TextInput
                        placeholder="Suche nach Bezeichnung oder FinVe-Nr."
                        value={search}
                        onChange={(e) => setSearch(e.currentTarget.value)}
                        w={320}
                    />
                    <SegmentedControl
                        data={[
                            { value: "all", label: "Alle" },
                            { value: "regular", label: "Regulär" },
                            { value: "sammel", label: "Sammel-FinVes" },
                        ]}
                        value={typeFilter}
                        onChange={(v) => setTypeFilter(v as TypeFilter)}
                    />
                </Group>

                {isLoading && <Group justify="center"><Loader /></Group>}
                {isError && (
                    <Alert color="red" variant="light" title="Fehler">
                        FinVe-Liste konnte nicht geladen werden.
                    </Alert>
                )}

                {!isLoading && !isError && (
                    <Stack gap="md">
                        <Text size="sm" c="dimmed">
                            {filtered.length} von {(finves ?? []).length} FinVes
                        </Text>

                        {filtered.length === 0 && (
                            <Text c="dimmed" ta="center" py="xl">
                                Keine FinVes gefunden.
                            </Text>
                        )}

                        {filtered.map((finve) => (
                            <FinveCard key={finve.id} finve={finve} />
                        ))}
                    </Stack>
                )}
            </Stack>
        </Container>
    );
}
