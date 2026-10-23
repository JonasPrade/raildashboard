import { type ReactNode, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import {
    Anchor,
    Badge,
    Button,
    Collapse,
    Group,
    Paper,
    Stack,
    Text,
    Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Link } from "react-router-dom";
import { useAuth } from "../../../lib/auth";
import {
    type FinveWithBudgets,
    useProjectFinvesWithSubprojects,
    useUpdateFinveProjects,
} from "../../../shared/api/queries";
import { openConfirmModal } from "../../../shared/ui/confirmModal";
import { FinveBudgetDetails } from "../../finves/shared/FinveBudgetDetails";
import FinveSearchSelect from "../../finves/shared/FinveSearchSelect";
import { formatTEuro } from "../../../shared/format";
import { LoadingState } from "../../../shared/ui/LoadingState";
import ProjectHoverCard from "../ProjectHoverCard";

// ---------------------------------------------------------------------------
// Hint on a FinVe that only a sub-project carries (parent projects aggregate)
// ---------------------------------------------------------------------------

function SubprojectHint({ finve }: { finve: FinveWithBudgets }) {
    if (!finve.from_subprojects || finve.subprojects.length === 0) return null;
    return (
        <Text size="xs" c="dimmed">
            {finve.subprojects.length === 1 ? "Aus Teilprojekt " : "Aus Teilprojekten "}
            {finve.subprojects.map((sub, i) => (
                <span key={sub.id}>
                    {i > 0 && ", "}
                    <ProjectHoverCard projectId={sub.id}>
                        <Anchor component={Link} to={`/projects/${sub.id}`} size="xs">
                            {sub.name}
                        </Anchor>
                    </ProjectHoverCard>
                </span>
            ))}
        </Text>
    );
}

// ---------------------------------------------------------------------------
// Single FinVe card with charts (chart/table internals live in
// features/finves/shared/FinveBudgetDetails, shared with the FinVe overview)
// ---------------------------------------------------------------------------

function FinveCard({ finve, action }: { finve: FinveWithBudgets; action?: ReactNode }) {
    const [open, setOpen] = useState(false);
    const hasBudgets = finve.budgets.length > 0;
    const lastBudget = finve.budgets.at(-1);

    // SammelFinVe: compact tag, linked to the FinVe overview (deep-linked by id).
    if (finve.is_sammel_finve) {
        return (
            <Stack gap={2}>
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
                <SubprojectHint finve={finve} />
                {action}
            </Stack>
        );
    }

    return (
        <Paper withBorder p="var(--card-pad)">
            <Stack gap="sm">
                <Group justify="space-between" align="flex-start" wrap="wrap">
                    <Stack gap={2}>
                        <Group gap="sm" align="center">
                            <Badge variant="outline">FinVe {finve.id}</Badge>
                            <Text size="sm" fw={500}>{finve.name ?? "–"}</Text>
                        </Group>
                        <SubprojectHint finve={finve} />
                    </Stack>
                    <Group gap="xl">
                        {action}
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
// Edit controls: remove an own permanent link, add a FinVe (finve.edit)
// ---------------------------------------------------------------------------

function useFinveLinkActions(projectId: number) {
    const updateLinks = useUpdateFinveProjects();

    const run = (finveId: number, change: { addProjectIds?: number[]; removeProjectIds?: number[] }, done: string) =>
        updateLinks.mutate(
            { finveId, ...change },
            {
                onSuccess: () => notifications.show({ color: "green", title: "FinVe-Zuordnung geändert", message: done }),
                onError: (err) =>
                    notifications.show({
                        color: "red",
                        title: "Ändern fehlgeschlagen",
                        message: (err as Error)?.message ?? "Unbekannter Fehler",
                    }),
            },
        );

    const remove = (finve: FinveWithBudgets) =>
        openConfirmModal({
            title: "Zuordnung entfernen",
            children: (
                <Text size="sm" mb="md">
                    Soll FinVe {finve.id} „{finve.name ?? "–"}“ von diesem Projekt gelöst werden? Die FinVe
                    selbst bleibt erhalten, der Planungsstand wird neu berechnet. Die Änderung steht im
                    Änderungsprotokoll und lässt sich dort zurücksetzen.
                </Text>
            ),
            labels: { confirm: "Entfernen", cancel: "Abbrechen" },
            danger: true,
            onConfirm: () =>
                run(finve.id, { removeProjectIds: [projectId] }, `FinVe ${finve.id} wurde vom Projekt gelöst.`),
        });

    const add = (finveId: number) =>
        run(finveId, { addProjectIds: [projectId] }, `FinVe ${finveId} wurde dem Projekt zugeordnet.`);

    return { remove, add, isPending: updateLinks.isPending };
}

function AddFinveRow({
    linkedIds,
    onAdd,
    loading,
}: {
    linkedIds: number[];
    onAdd: (finveId: number) => void;
    loading: boolean;
}) {
    const [selected, setSelected] = useState<number | null>(null);
    return (
        <Group align="flex-end" gap="sm" wrap="wrap">
            <FinveSearchSelect
                label="FinVe hinzufügen"
                value={selected}
                onChange={setSelected}
                excludeIds={linkedIds}
                style={{ flex: "1 1 260px" }}
            />
            <Button
                disabled={selected == null}
                loading={loading}
                onClick={() => {
                    if (selected == null) return;
                    onAdd(selected);
                    setSelected(null);
                }}
            >
                Hinzufügen
            </Button>
        </Group>
    );
}

// ---------------------------------------------------------------------------
// Public section component
// ---------------------------------------------------------------------------

export default function FinveSection({ projectId }: { projectId: number }) {
    // A parent project shows the FinVes of all its sub-projects too, own ones first.
    const { data: finves, isLoading } = useProjectFinvesWithSubprojects(projectId);
    const { can } = useAuth();
    const canEditLinks = can("finve.edit");
    const [editing, setEditing] = useState(false);
    const actions = useFinveLinkActions(projectId);

    if (isLoading) return <LoadingState rows={3} />;
    if ((!finves || finves.length === 0) && !canEditLinks) return null;
    const ordered = [...(finves ?? [])].sort((a, b) => Number(a.from_subprojects) - Number(b.from_subprojects));
    const ownIds = ordered.filter((f) => f.linked_permanently).map((f) => f.id);

    // Only the project's own permanent links can be removed here: inherited ones
    // live on the sub-project (linked in the hint), Sammel-FinVe year links come
    // from the Haushalt import.
    const removeAction = (finve: FinveWithBudgets) =>
        editing && finve.linked_permanently ? (
            <Button
                size="xs"
                variant="default"
                color="red"
                onClick={() => actions.remove(finve)}
                disabled={actions.isPending}
            >
                Zuordnung entfernen
            </Button>
        ) : undefined;

    return (
        <Paper withBorder p="var(--card-pad)">
            <Stack gap="md">
                <Group justify="space-between" align="center" wrap="wrap">
                    <Title order={2}>Finanzierungsvereinbarungen (FinVe)</Title>
                    {canEditLinks && (
                        <Button variant={editing ? "filled" : "default"} size="xs" onClick={() => setEditing((e) => !e)}>
                            {editing ? "Fertig" : "Zuordnung bearbeiten"}
                        </Button>
                    )}
                </Group>
                {editing && (
                    <AddFinveRow linkedIds={ownIds} onAdd={actions.add} loading={actions.isPending} />
                )}
                {ordered.length === 0 && (
                    <Text size="sm" c="dimmed">Diesem Projekt ist keine FinVe zugeordnet.</Text>
                )}
                {ordered.map((finve) => (
                    <FinveCard key={finve.id} finve={finve} action={removeAction(finve)} />
                ))}
            </Stack>
        </Paper>
    );
}
