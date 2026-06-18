import { useState } from "react";
import {
    ActionIcon,
    Anchor,
    Badge,
    Button,
    Collapse,
    Divider,
    Group,
    NumberInput,
    Select,
    Stack,
    Table,
    Text,
    TextInput,
} from "@mantine/core";
import { Link } from "react-router-dom";
import { IconChevronDown, IconChevronRight, IconPlus, IconTrash } from "@tabler/icons-react";

import {
    type ProgressChild,
    type ProgressObservation,
    type SourceContribution,
    useAddProgressObservation,
    useDeleteProgressObservation,
} from "../../../../shared/api/queries";
import {
    MAIN_PHASES,
    MAIN_PHASE_LABEL,
    MAIN_PHASE_SHORT,
    PARALLEL_STATES,
    PARALLEL_STATE_LABEL,
    SOURCE_LABEL,
    TRACK_LABEL,
    type MainPhase,
    type ObservationTrack,
    type SourceType,
    stateLabel,
} from "./phaseMeta";

function ContributionRow({ c }: { c: SourceContribution }) {
    return (
        <Table.Tr>
            <Table.Td>
                <Badge size="sm" variant="light">
                    {SOURCE_LABEL[c.source_type as SourceType] ?? c.source_type}
                </Badge>
            </Table.Td>
            <Table.Td>{TRACK_LABEL[c.track as ObservationTrack] ?? c.track}</Table.Td>
            <Table.Td>{stateLabel(c.track as ObservationTrack, c.asserted_state)}</Table.Td>
            <Table.Td>{c.observed_date ?? "–"}</Table.Td>
            <Table.Td>{(c.effective_confidence * 100).toFixed(0)} %</Table.Td>
            <Table.Td>
                {c.was_decisive && (
                    <Badge size="sm" color="blue">
                        entscheidend
                    </Badge>
                )}
            </Table.Td>
        </Table.Tr>
    );
}

// Source types that can be captured manually. VIB/FINVE are materialised from
// imports and are therefore not offered here.
const MANUAL_SOURCE_TYPES: SourceType[] = ["MANUELL", "FULDA_RUNDE", "BAUPORTAL", "MEDIEN"];

function AddObservationForm({ projectId }: { projectId: number }) {
    const [sourceType, setSourceType] = useState<SourceType>("MANUELL");
    const [track, setTrack] = useState<ObservationTrack>("MAIN");
    const [state, setState] = useState<string>("VORPLANUNG");
    const [date, setDate] = useState("");
    const [confidence, setConfidence] = useState<string>("");
    const [note, setNote] = useState("");
    const add = useAddProgressObservation(projectId);

    const stateOptions =
        track === "MAIN"
            ? MAIN_PHASES.map((p) => ({ value: p, label: MAIN_PHASE_LABEL[p] }))
            : PARALLEL_STATES.map((s) => ({ value: s, label: PARALLEL_STATE_LABEL[s] }));

    const submit = () => {
        const conf = confidence.trim() === "" ? null : Number(confidence);
        add.mutate(
            {
                source_type: sourceType,
                track,
                asserted_state: state,
                observed_date: date || null,
                confidence: conf !== null && Number.isFinite(conf) ? conf : null,
                note: note || null,
            },
            {
                onSuccess: () => {
                    setNote("");
                    setDate("");
                    setConfidence("");
                },
            },
        );
    };

    return (
        <Group gap="sm" align="flex-end" wrap="wrap">
            <Select
                size="xs"
                label="Quelle"
                value={sourceType}
                onChange={(v) => setSourceType((v as SourceType) ?? "MANUELL")}
                data={MANUAL_SOURCE_TYPES.map((s) => ({ value: s, label: SOURCE_LABEL[s] }))}
                w={140}
            />
            <Select
                size="xs"
                label="Spur"
                value={track}
                onChange={(v) => {
                    const t = (v as ObservationTrack) ?? "MAIN";
                    setTrack(t);
                    setState(t === "MAIN" ? "VORPLANUNG" : "OFFEN");
                }}
                data={[
                    { value: "MAIN", label: TRACK_LABEL.MAIN },
                    { value: "PF", label: TRACK_LABEL.PF },
                    { value: "PARL", label: TRACK_LABEL.PARL },
                ]}
                w={150}
            />
            <Select
                size="xs"
                label="Aussage"
                value={state}
                onChange={(v) => setState(v ?? stateOptions[0].value)}
                data={stateOptions}
                w={180}
            />
            <TextInput
                size="xs"
                type="date"
                label="Datum"
                value={date}
                onChange={(e) => setDate(e.currentTarget.value)}
                w={150}
            />
            <NumberInput
                size="xs"
                label="Vertrauen"
                description="0–1, optional"
                value={confidence}
                onChange={(v) => setConfidence(v === "" ? "" : String(v))}
                min={0}
                max={1}
                step={0.1}
                decimalScale={2}
                w={110}
            />
            <TextInput
                size="xs"
                label="Notiz / Quelle"
                value={note}
                onChange={(e) => setNote(e.currentTarget.value)}
                w={200}
            />
            <Button
                size="xs"
                leftSection={<IconPlus size={14} />}
                onClick={submit}
                loading={add.isPending}
            >
                Beobachtung
            </Button>
        </Group>
    );
}

function ObservationRow({
    projectId,
    obs,
    canEdit,
}: {
    projectId: number;
    obs: ProgressObservation;
    canEdit: boolean;
}) {
    const del = useDeleteProgressObservation(projectId);
    return (
        <Table.Tr>
            <Table.Td>
                <Badge size="sm" variant="light">
                    {SOURCE_LABEL[obs.source_type as SourceType] ?? obs.source_type}
                </Badge>
            </Table.Td>
            <Table.Td>{TRACK_LABEL[obs.track as ObservationTrack] ?? obs.track}</Table.Td>
            <Table.Td>{stateLabel(obs.track as ObservationTrack, obs.asserted_state)}</Table.Td>
            <Table.Td>{obs.observed_date ?? "–"}</Table.Td>
            <Table.Td>{obs.note ?? ""}</Table.Td>
            <Table.Td>
                {canEdit && !obs.is_derived && (
                    <ActionIcon
                        variant="subtle"
                        color="red"
                        size="sm"
                        aria-label="Beobachtung löschen"
                        onClick={() => del.mutate(obs.id)}
                    >
                        <IconTrash size={14} />
                    </ActionIcon>
                )}
                {obs.is_derived && (
                    <Badge size="xs" color="gray" title="Aus Import abgeleitet – nicht manuell löschbar">
                        abgeleitet
                    </Badge>
                )}
            </Table.Td>
        </Table.Tr>
    );
}

type Props = {
    projectId: number;
    contributions: SourceContribution[];
    observations: ProgressObservation[];
    children?: ProgressChild[];
    isSuperior: boolean;
    canEdit: boolean;
};

export default function SourceBreakdown({
    projectId,
    contributions,
    observations,
    children = [],
    isSuperior,
    canEdit,
}: Props) {
    const [open, setOpen] = useState(false);

    return (
        <Stack gap="xs">
            <Button
                variant="subtle"
                size="xs"
                px={0}
                leftSection={open ? <IconChevronDown size={16} /> : <IconChevronRight size={16} />}
                onClick={() => setOpen((o) => !o)}
                style={{ alignSelf: "flex-start" }}
            >
                Quellen &amp; Beobachtungen ({contributions.length})
            </Button>

            <Collapse in={open}>
                <Stack gap="md">
                    {isSuperior && children.length > 0 && (
                        <Stack gap={4}>
                            <Text size="sm" fw={600}>
                                Unterprojekte
                            </Text>
                            {children.map((child) => (
                                <Group key={child.project_id} gap="sm">
                                    <Anchor component={Link} to={`/projects/${child.project_id}`} size="sm">
                                        {child.name}
                                    </Anchor>
                                    <Badge size="sm" variant="light">
                                        {MAIN_PHASE_SHORT[child.effective_phase as MainPhase] ??
                                            child.effective_phase}
                                    </Badge>
                                    {child.lifecycle_status !== "AKTIV" && (
                                        <Badge size="xs" color="orange">
                                            {child.lifecycle_status}
                                        </Badge>
                                    )}
                                </Group>
                            ))}
                            <Divider my="xs" />
                        </Stack>
                    )}

                    {contributions.length > 0 ? (
                        <Table striped withTableBorder>
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>Quelle</Table.Th>
                                    <Table.Th>Spur</Table.Th>
                                    <Table.Th>Aussage</Table.Th>
                                    <Table.Th>Datum</Table.Th>
                                    <Table.Th>Vertrauen</Table.Th>
                                    <Table.Th></Table.Th>
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {contributions.map((c, i) => (
                                    <ContributionRow key={c.observation_id ?? i} c={c} />
                                ))}
                            </Table.Tbody>
                        </Table>
                    ) : (
                        <Text size="sm" c="dimmed">
                            Noch keine Beobachtungen erfasst.
                        </Text>
                    )}

                    {canEdit && (
                        <>
                            <Divider label="Manuelle Beobachtungen" labelPosition="left" />
                            <AddObservationForm projectId={projectId} />
                            {observations.length > 0 && (
                                <Table>
                                    <Table.Thead>
                                        <Table.Tr>
                                            <Table.Th>Quelle</Table.Th>
                                            <Table.Th>Spur</Table.Th>
                                            <Table.Th>Aussage</Table.Th>
                                            <Table.Th>Datum</Table.Th>
                                            <Table.Th>Notiz</Table.Th>
                                            <Table.Th></Table.Th>
                                        </Table.Tr>
                                    </Table.Thead>
                                    <Table.Tbody>
                                        {observations.map((obs) => (
                                            <ObservationRow
                                                key={obs.id}
                                                projectId={projectId}
                                                obs={obs}
                                                canEdit={canEdit}
                                            />
                                        ))}
                                    </Table.Tbody>
                                </Table>
                            )}
                        </>
                    )}
                </Stack>
            </Collapse>
        </Stack>
    );
}
