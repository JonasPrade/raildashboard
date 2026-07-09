import {
    Alert,
    Badge,
    Container,
    Group,
    Loader,
    Select,
    Stack,
    Table,
    Text,
} from "@mantine/core";

import { ChronicleCard, ChronicleHeadline } from "../../components/chronicle";
import RequirePermission from "../../components/RequirePermission";
import {
    type SammelFinveProgress,
    useSammelFinveProgress,
    useSetFinveProgressPhase,
} from "../../shared/api/queries";
import {
    MAIN_PHASE_LABEL,
    mainPhaseOptions,
    type MainPhase,
} from "../projects/components/progress/phaseMeta";

const AUTO = "__auto__";

const PHASE_OPTIONS = [
    { value: AUTO, label: "— automatisch —" },
    ...mainPhaseOptions(),
];

function PhaseBadge({ value, dimmed }: { value: string | null | undefined; dimmed?: boolean }) {
    if (!value) {
        return (
            <Badge variant="outline" color="gray">
                unbestimmt
            </Badge>
        );
    }
    return (
        <Badge variant={dimmed ? "outline" : "light"} color={dimmed ? "gray" : "indigo"}>
            {MAIN_PHASE_LABEL[value as MainPhase] ?? value}
        </Badge>
    );
}

function Row({ finve }: { finve: SammelFinveProgress }) {
    const setPhase = useSetFinveProgressPhase();
    return (
        <Table.Tr style={finve.needs_assignment ? { backgroundColor: "rgba(250, 176, 5, 0.08)" } : undefined}>
            <Table.Td>
                <Group gap={6}>
                    <Badge variant="light">FinVe {finve.finve_id}</Badge>
                    <Text size="sm">{finve.name ?? "–"}</Text>
                </Group>
            </Table.Td>
            <Table.Td>
                {finve.projects.length === 0 ? (
                    <Text size="xs" c="dimmed">
                        keine
                    </Text>
                ) : (
                    <Text size="xs">
                        {finve.projects.map((p) => p.name).join(", ")}
                    </Text>
                )}
            </Table.Td>
            <Table.Td>
                <PhaseBadge value={finve.auto_phase} dimmed />
            </Table.Td>
            <Table.Td>
                <Select
                    size="xs"
                    w={190}
                    data={PHASE_OPTIONS}
                    value={finve.progress_phase ?? AUTO}
                    disabled={setPhase.isPending}
                    onChange={(v) =>
                        setPhase.mutate({
                            finveId: finve.finve_id,
                            phase: !v || v === AUTO ? null : v,
                        })
                    }
                />
            </Table.Td>
            <Table.Td>
                <PhaseBadge value={finve.effective_phase} />
            </Table.Td>
        </Table.Tr>
    );
}

function FinveProgressAdminPageContent() {
    const { data, isLoading } = useSammelFinveProgress();

    const rows = data ?? [];
    const needing = rows.filter((r) => r.needs_assignment).length;

    return (
        <Container size="lg" py="xl">
            <Stack gap="lg">
                <Stack gap={4}>
                    <ChronicleHeadline as="h1">Sammel-FinVe · Phasen-Zuordnung</ChronicleHeadline>
                    <Text size="sm" c="dimmed">
                        Sammel-FinVes treiben den Planungsstand verknüpfter Projekte. Die Phase wird
                        aus der Leistungsphase im Namen erkannt (Lph 1/2 → Vorplanung, Lph 3/4 →
                        Genehmigungsplanung). Lässt sich keine Phase erkennen (z. B. EKrG), kann sie
                        hier manuell zugeordnet werden.
                    </Text>
                </Stack>

                {needing > 0 && (
                    <Alert color="orange" variant="light">
                        {needing} Sammel-FinVe(s) ohne erkennbare Leistungsphase – bitte manuell zuordnen
                        (gelb markiert).
                    </Alert>
                )}

                <ChronicleCard>
                    {isLoading ? (
                        <Group justify="center" py="md">
                            <Loader size="sm" />
                        </Group>
                    ) : (
                        <Table striped highlightOnHover>
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>Sammel-FinVe</Table.Th>
                                    <Table.Th>Projekte</Table.Th>
                                    <Table.Th>Erkannt</Table.Th>
                                    <Table.Th>Manuelle Zuordnung</Table.Th>
                                    <Table.Th>Effektiv</Table.Th>
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {rows.map((finve) => (
                                    <Row key={finve.finve_id} finve={finve} />
                                ))}
                            </Table.Tbody>
                        </Table>
                    )}
                </ChronicleCard>
            </Stack>
        </Container>
    );
}

export default function FinveProgressAdminPage() {
    return (
        <RequirePermission
            perm="progress.edit"
            message={'Sie benötigen die Berechtigung „Planungsstand bearbeiten".'}
        >
            <FinveProgressAdminPageContent />
        </RequirePermission>
    );
}
