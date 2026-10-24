import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import {
    Badge,
    Button,
    Collapse,
    Group,
    Paper,
    SegmentedControl,
    Stack,
    Text,
    TextInput,
    Title,
    UnstyledButton,
} from "@mantine/core";
import { useAuth } from "../../lib/auth";
import { useFinves, type FinveListItem } from "../../shared/api/queries";
import { useIsMobile } from "../../shared/hooks/useBreakpoint";
import { FinveBudgetDetails } from "./shared/FinveBudgetDetails";
import { formatTEuro } from "../../shared/format";
import { LinkedProjects } from "../../shared/ui/LinkedProjects";
import { LoadingState } from "../../shared/ui/LoadingState";
import { ErrorState } from "../../shared/ui/ErrorState";
import ProjectHoverCard from "../projects/ProjectHoverCard";
import FinveProjectsDrawer from "./FinveProjectsDrawer";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type TypeFilter = "all" | "regular" | "sammel";

// ---------------------------------------------------------------------------
// Single FinVe card (chart/table internals live in shared/FinveBudgetDetails,
// shared with the project-detail FinveSection)
// ---------------------------------------------------------------------------

function FinveCard({ finve, onEditProjects }: { finve: FinveListItem; onEditProjects?: () => void }) {
    const [open, setOpen] = useState(false);

    const hasBudgets = finve.budgets.length > 0;
    const lastBudget = finve.budgets.at(-1);

    return (
        <Paper withBorder p="var(--card-pad)">
            <Stack gap="md">
                {/* ── Header row ─────────────────────────────────────────── */}
                <Group justify="space-between" align="flex-start" wrap="wrap" gap="sm">
                    <Stack gap={4}>
                        <Group gap="sm" align="center">
                            <Badge variant="outline">{finve.id}</Badge>
                            {finve.is_sammel_finve && (
                                <Badge variant="outline">Sammel-FinVe</Badge>
                            )}
                            {finve.temporary_finve_number && (
                                <Badge variant="outline">vorläufig</Badge>
                            )}
                        </Group>
                        <Text fw={600} size="md" lh={1.3}>
                            {finve.name ?? "—"}
                        </Text>
                    </Stack>

                    <Group gap="lg" align="flex-start" wrap="wrap">
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
                <LinkedProjects
                    projects={finve.projects}
                    wrapLink={(id, link) => <ProjectHoverCard projectId={id}>{link}</ProjectHoverCard>}
                />
                {onEditProjects && (
                    <Button size="xs" variant="default" onClick={onEditProjects} style={{ alignSelf: "flex-start" }}>
                        Projekte bearbeiten
                    </Button>
                )}

                {/* ── Expandable charts / budget details ─────────────────── */}
                {hasBudgets && (
                    <>
                        <UnstyledButton
                            onClick={() => setOpen((o) => !o)}
                            style={{ alignSelf: "flex-start" }}
                        >
                            <Text size="sm" c="blue" style={{ display: "inline-flex", alignItems: "center", gap: 4, userSelect: "none" }}>
                                {open ? <ChevronUp size={16} aria-hidden /> : <ChevronDown size={16} aria-hidden />}
                                {open ? "Diagramme ausblenden" : "Details & Diagramme"}
                            </Text>
                        </UnstyledButton>

                        <Collapse in={open}>
                            <FinveBudgetDetails budgets={finve.budgets} />
                        </Collapse>
                    </>
                )}
            </Stack>
        </Paper>
    );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function FinveOverviewPage() {
    const isMobile = useIsMobile();
    const [searchParams] = useSearchParams();
    const [search, setSearch] = useState(searchParams.get("q") ?? "");
    const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");

    const { data: finves, isLoading, isError, refetch } = useFinves();
    const { can } = useAuth();
    const canEditLinks = can("finve.edit");
    // Id, not object: the drawer reads the refetched list after every change.
    const [editingId, setEditingId] = useState<number | null>(null);
    const editing = (finves ?? []).find((f) => f.id === editingId) ?? null;

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
        <Stack gap="lg" py="lg">
                <Title order={2}>Finanzierungsvereinbarungen</Title>

                <Group wrap="wrap" gap="sm">
                    <TextInput
                        placeholder="Suche nach Bezeichnung oder FinVe-Nr."
                        value={search}
                        onChange={(e) => setSearch(e.currentTarget.value)}
                        flex="1 1 260px"
                    />
                    <SegmentedControl
                        data={[
                            { value: "all", label: "Alle" },
                            { value: "regular", label: "Regulär" },
                            { value: "sammel", label: "Sammel-FinVes" },
                        ]}
                        value={typeFilter}
                        onChange={(v) => setTypeFilter(v as TypeFilter)}
                        fullWidth={isMobile}
                        style={isMobile ? { width: "100%" } : undefined}
                    />
                </Group>

                {isLoading && <LoadingState rows={6} />}
                {isError && (
                    <ErrorState onRetry={() => void refetch()}>FinVe-Liste konnte nicht geladen werden.</ErrorState>
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
                            <FinveCard
                                key={finve.id}
                                finve={finve}
                                onEditProjects={canEditLinks ? () => setEditingId(finve.id) : undefined}
                            />
                        ))}
                    </Stack>
                )}
                <FinveProjectsDrawer finve={editing} onClose={() => setEditingId(null)} />
        </Stack>
    );
}
