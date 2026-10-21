import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import {
    Anchor,
    Badge,
    Collapse,
    Group,
    Paper,
    Stack,
    Text,
    Title,
} from "@mantine/core";
import { Link } from "react-router-dom";
import { type FinveWithBudgets, useProjectFinves } from "../../../shared/api/queries";
import { FinveBudgetDetails } from "../../finves/shared/FinveBudgetDetails";
import { formatTEuro } from "../../../shared/format";
import { LoadingState } from "../../../shared/ui/LoadingState";

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
                to={`/finanzen/bedarfsplan?q=${finve.id}`}
                underline="never"
                style={{ color: "inherit" }}
            >
                <Group gap="xs" align="center">
                    <Badge variant="outline">Sammel-FinVe</Badge>
                    <Badge variant="outline">FinVe {finve.id}</Badge>
                    <Text size="sm" c="dimmed">{finve.name ?? "–"}</Text>
                </Group>
            </Anchor>
        );
    }

    return (
        <Paper withBorder p="var(--card-pad)">
            <Stack gap="sm">
                <Group justify="space-between" align="flex-start" wrap="wrap">
                    <Group gap="sm" align="center">
                        <Badge variant="outline">FinVe {finve.id}</Badge>
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
                                style={{ display: "inline-flex", alignItems: "center", gap: 4, cursor: "pointer", userSelect: "none" }}
                                onClick={() => setOpen((o) => !o)}
                            >
                                {open ? "Ausblenden" : "Details & Diagramme"}
                                {open ? <ChevronUp size={16} aria-hidden /> : <ChevronDown size={16} aria-hidden />}
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
        </Paper>
    );
}

// ---------------------------------------------------------------------------
// Public section component
// ---------------------------------------------------------------------------

export default function FinveSection({ projectId }: { projectId: number }) {
    const { data: finves, isLoading } = useProjectFinves(projectId);

    if (isLoading) return <LoadingState rows={3} />;
    if (!finves || finves.length === 0) return null;

    return (
        <Paper withBorder p="var(--card-pad)">
            <Stack gap="md">
                <Title order={2}>Finanzierungsvereinbarungen (FinVe)</Title>
                {finves.map((finve) => (
                    <FinveCard key={finve.id} finve={finve} />
                ))}
            </Stack>
        </Paper>
    );
}
