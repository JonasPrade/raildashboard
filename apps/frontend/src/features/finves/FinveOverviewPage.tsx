import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
    Alert,
    Collapse,
    Container,
    Group,
    Loader,
    SegmentedControl,
    Stack,
    Text,
    TextInput,
    UnstyledButton,
} from "@mantine/core";
import { ChronicleHeadline, ChronicleCard, ChronicleDataChip } from "../../components/chronicle";
import { useFinves, type FinveListItem } from "../../shared/api/queries";
import { FinveBudgetDetails } from "./shared/FinveBudgetDetails";
import { formatTEuro } from "../../shared/format";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type TypeFilter = "all" | "regular" | "sammel";

// ---------------------------------------------------------------------------
// Single FinVe card (chart/table internals live in shared/FinveBudgetDetails,
// shared with the project-detail FinveSection)
// ---------------------------------------------------------------------------

function FinveCard({ finve }: { finve: FinveListItem }) {
    const [open, setOpen] = useState(false);

    const hasBudgets = finve.budgets.length > 0;
    const lastBudget = finve.budgets.at(-1);

    return (
        <ChronicleCard>
            <Stack gap="md">
                {/* ── Header row ─────────────────────────────────────────── */}
                <Group justify="space-between" align="flex-start" wrap="wrap" gap="sm">
                    <Stack gap={4}>
                        <Group gap="sm" align="center">
                            <ChronicleDataChip>
                                {finve.id}
                            </ChronicleDataChip>
                            {finve.is_sammel_finve && (
                                <ChronicleDataChip>Sammel-FinVe</ChronicleDataChip>
                            )}
                            {finve.temporary_finve_number && (
                                <ChronicleDataChip>vorläufig</ChronicleDataChip>
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
                                <Text size="sm" fw={600}>{formatTEuro(finve.cost_estimate_original)}</Text>
                            </Stack>
                        )}
                        {lastBudget?.cost_estimate_actual != null && (
                            <Stack gap={2} align="flex-end">
                                <Text size="xs" c="dimmed">Aktuell ({lastBudget.budget_year})</Text>
                                <Text size="sm" fw={600}>{formatTEuro(lastBudget.cost_estimate_actual)}</Text>
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
                                <Link
                                    key={p.id}
                                    to={`/projects/${p.id}`}
                                    style={{
                                        textDecoration: "none",
                                        cursor: "pointer",
                                        display: "inline-flex",
                                        alignItems: "center",
                                        gap: 6,
                                        padding: "4px 8px",
                                        border: "1px solid var(--mantine-color-default-border)",
                                        borderRadius: 4,
                                        transition: "background 0.15s",
                                    }}
                                >
                                    <Text size="xs" c="dimmed" ff="monospace">{p.id}</Text>
                                    <Text size="xs" fw={500} c="dark">{p.name}</Text>
                                </Link>
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
                            <FinveBudgetDetails budgets={finve.budgets} />
                        </Collapse>
                    </>
                )}
            </Stack>
        </ChronicleCard>
    );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function FinveOverviewPage() {
    const [searchParams] = useSearchParams();
    const [search, setSearch] = useState(searchParams.get("q") ?? "");
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
                <ChronicleHeadline as="h1">Finanzierungsvereinbarungen</ChronicleHeadline>

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
