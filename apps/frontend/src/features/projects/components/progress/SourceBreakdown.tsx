import { useState } from "react";
import { Badge, Button, Collapse, Divider, Group, Stack, Table, Text } from "@mantine/core";
import { IconChevronDown, IconChevronRight } from "@tabler/icons-react";

import { useAuth } from "../../../../lib/auth";
import {
    type ProgressObservation,
    type SourceContribution,
} from "../../../../shared/api/queries";
import {
    SOURCE_LABEL,
    TRACK_LABEL,
    formatTimestamp,
    stateLabel,
    type ObservationTrack,
    type SourceType,
} from "./phaseMeta";

// ``showInternal`` reveals the editorial confidence / decisive columns, which
// are only meaningful to logged-in editors (not shown to the public).
function ContributionRow({ c, showInternal }: { c: SourceContribution; showInternal: boolean }) {
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
            {showInternal && (
                <>
                    <Table.Td>{(c.effective_confidence * 100).toFixed(0)} %</Table.Td>
                    <Table.Td>
                        {c.was_decisive && (
                            <Badge size="sm" color="blue">
                                entscheidend
                            </Badge>
                        )}
                    </Table.Td>
                </>
            )}
        </Table.Tr>
    );
}

type Props = {
    contributions: SourceContribution[];
    observations: ProgressObservation[];
};

export default function SourceBreakdown({ contributions, observations }: Props) {
    const { user } = useAuth();
    const showInternal = user !== null;
    const [open, setOpen] = useState(false);

    // Manual (non-derived) observations carry editorial provenance so a reader
    // can judge whether a transcription is current or stale.
    const manual = observations.filter((o) => !o.is_derived);

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
                    {contributions.length > 0 ? (
                        <Table striped withTableBorder>
                            <Table.Thead>
                                <Table.Tr>
                                    <Table.Th>Quelle</Table.Th>
                                    <Table.Th>Bereich</Table.Th>
                                    <Table.Th>Aussage</Table.Th>
                                    <Table.Th>Datum</Table.Th>
                                    {showInternal && (
                                        <>
                                            <Table.Th>Vertrauen</Table.Th>
                                            <Table.Th></Table.Th>
                                        </>
                                    )}
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {contributions.map((c, i) => (
                                    <ContributionRow
                                        key={c.observation_id ?? i}
                                        c={c}
                                        showInternal={showInternal}
                                    />
                                ))}
                            </Table.Tbody>
                        </Table>
                    ) : (
                        <Text size="sm" c="dimmed">
                            Noch keine Beobachtungen erfasst.
                        </Text>
                    )}

                    {manual.length > 0 && (
                        <>
                            <Divider label="Manuelle Beobachtungen" labelPosition="left" />
                            <Table>
                                <Table.Thead>
                                    <Table.Tr>
                                        <Table.Th>Quelle</Table.Th>
                                        <Table.Th>Bereich</Table.Th>
                                        <Table.Th>Aussage</Table.Th>
                                        <Table.Th>Datum</Table.Th>
                                        <Table.Th>Notiz</Table.Th>
                                        <Table.Th>Erfasst von</Table.Th>
                                        <Table.Th>Erfasst am</Table.Th>
                                    </Table.Tr>
                                </Table.Thead>
                                <Table.Tbody>
                                    {manual.map((obs) => (
                                        <Table.Tr key={obs.id}>
                                            <Table.Td>
                                                <Badge size="sm" variant="light">
                                                    {SOURCE_LABEL[obs.source_type as SourceType] ??
                                                        obs.source_type}
                                                </Badge>
                                            </Table.Td>
                                            <Table.Td>
                                                {TRACK_LABEL[obs.track as ObservationTrack] ?? obs.track}
                                            </Table.Td>
                                            <Table.Td>
                                                <Group gap={6} wrap="nowrap">
                                                    {stateLabel(obs.track as ObservationTrack, obs.asserted_state)}
                                                    {obs.is_expected && (
                                                        <Badge size="xs" color="teal" variant="light">
                                                            erwartet
                                                        </Badge>
                                                    )}
                                                </Group>
                                            </Table.Td>
                                            <Table.Td>{obs.observed_date ?? "–"}</Table.Td>
                                            <Table.Td>{obs.note ?? ""}</Table.Td>
                                            <Table.Td>{obs.username_snapshot ?? "–"}</Table.Td>
                                            <Table.Td>{formatTimestamp(obs.created_at)}</Table.Td>
                                        </Table.Tr>
                                    ))}
                                </Table.Tbody>
                            </Table>
                        </>
                    )}
                </Stack>
            </Collapse>
        </Stack>
    );
}
