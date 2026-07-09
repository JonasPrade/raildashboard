import { useState } from "react";
import {
    Anchor,
    Collapse,
    Group,
    Loader,
    Stack,
    Text,
    Title,
} from "@mantine/core";
import { Link } from "react-router-dom";
import { ChronicleCard, ChronicleDataChip } from "../../../components/chronicle";
import { type FinveWithBudgets, useProjectFinves } from "../../../shared/api/queries";
import { FinveBudgetDetails } from "../../finves/shared/FinveBudgetDetails";
import { formatTEuro } from "../../../shared/format";

// ---------------------------------------------------------------------------
// Single FinVe card with charts (chart/table internals live in
// features/finves/shared/FinveBudgetDetails, shared with the FinVe overview)
// ---------------------------------------------------------------------------

function FinveCard({ finve }: { finve: FinveWithBudgets }) {
    const [open, setOpen] = useState(false);
    const hasBudgets = finve.budgets.length > 0;
    const lastBudget = finve.budgets.at(-1);

    // SammelFinVe: compact tag, linked to the FinVe overview (deep-linked by id).
    if (finve.is_sammel_finve) {
        return (
            <Anchor
                component={Link}
                to={`/finves?q=${finve.id}`}
                underline="never"
                style={{ color: "inherit" }}
            >
                <Group gap="xs" align="center">
                    <ChronicleDataChip>Sammel-FinVe</ChronicleDataChip>
                    <ChronicleDataChip>FinVe {finve.id}</ChronicleDataChip>
                    <Text size="sm" c="dimmed">{finve.name ?? "–"}</Text>
                </Group>
            </Anchor>
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
                                <Text size="sm" fw={500}>{formatTEuro(finve.cost_estimate_original)}</Text>
                            </Stack>
                        )}
                        {lastBudget?.cost_estimate_actual != null && (
                            <Stack gap={0} align="flex-end">
                                <Text size="xs" c="dimmed">Aktuelle Kosten ({lastBudget.budget_year})</Text>
                                <Text size="sm" fw={500}>{formatTEuro(lastBudget.cost_estimate_actual)}</Text>
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
                        <FinveBudgetDetails budgets={finve.budgets} tabsMt="xs" />
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
