import { useState } from "react";
import { ActionIcon, Anchor, Badge, Group, Stack, Text, TextInput } from "@mantine/core";
import { IconExternalLink, IconPlus, IconTrash } from "@tabler/icons-react";

import { API_BASE } from "../../../../shared/api/client";
import {
    type TrackDocument,
    useLinkTrackDocument,
    useUnlinkTrackDocument,
} from "../../../../shared/api/queries";
import { PARALLEL_STATE_LABEL, type ParallelState } from "./phaseMeta";

type LaneTrack = "PF" | "PARL";

const STATE_COLOR: Record<ParallelState, string> = {
    OFFEN: "gray",
    LAEUFT: "blue",
    ABGESCHLOSSEN: "green",
};

function DocumentLink({ doc }: { doc: TrackDocument }) {
    const href = doc.document.file_path.startsWith("http")
        ? doc.document.file_path
        : `${API_BASE}${doc.document.file_path}`;
    return (
        <Anchor href={href} target="_blank" rel="noreferrer" size="sm">
            <Group gap={4} wrap="nowrap" component="span">
                <IconExternalLink size={14} />
                {doc.document.title}
            </Group>
        </Anchor>
    );
}

function Lane({
    projectId,
    track,
    label,
    state,
    documents,
    canEdit,
}: {
    projectId: number;
    track: LaneTrack;
    label: string;
    state: ParallelState | null;
    documents: TrackDocument[];
    canEdit: boolean;
}) {
    const [docId, setDocId] = useState("");
    const link = useLinkTrackDocument(projectId);
    const unlink = useUnlinkTrackDocument(projectId);

    const submit = () => {
        const id = Number(docId);
        if (Number.isFinite(id) && id > 0) {
            link.mutate({ track, documentId: id }, { onSuccess: () => setDocId("") });
        }
    };

    return (
        <Stack gap={6}>
            <Group gap="sm" align="center">
                <Text size="sm" fw={600} style={{ minWidth: 190 }}>
                    {label}
                </Text>
                <Badge color={state ? STATE_COLOR[state] : "gray"} variant="light">
                    {state ? PARALLEL_STATE_LABEL[state] : "–"}
                </Badge>
            </Group>

            {documents.length > 0 && (
                <Stack gap={2} pl={8}>
                    {documents.map((doc) => (
                        <Group key={doc.id} gap={6} wrap="nowrap">
                            <DocumentLink doc={doc} />
                            {canEdit && (
                                <ActionIcon
                                    variant="subtle"
                                    color="red"
                                    size="sm"
                                    aria-label="Dokument entfernen"
                                    onClick={() =>
                                        unlink.mutate({ track, documentId: doc.document.id })
                                    }
                                >
                                    <IconTrash size={14} />
                                </ActionIcon>
                            )}
                        </Group>
                    ))}
                </Stack>
            )}

            {canEdit && (
                <Group gap={6} pl={8}>
                    <TextInput
                        size="xs"
                        placeholder="Dokument-ID"
                        value={docId}
                        onChange={(e) => setDocId(e.currentTarget.value)}
                        w={120}
                    />
                    <ActionIcon
                        variant="light"
                        size="sm"
                        aria-label="Dokument verknüpfen"
                        onClick={submit}
                        loading={link.isPending}
                    >
                        <IconPlus size={14} />
                    </ActionIcon>
                </Group>
            )}
        </Stack>
    );
}

type Props = {
    projectId: number;
    hasPf: boolean;
    pfState: ParallelState | null;
    parlRelevant: boolean;
    parlState: ParallelState | null;
    pfDocuments: TrackDocument[];
    parlDocuments: TrackDocument[];
    canEdit: boolean;
};

export default function ParallelLanes({
    projectId,
    hasPf,
    pfState,
    parlRelevant,
    parlState,
    pfDocuments,
    parlDocuments,
    canEdit,
}: Props) {
    if (!hasPf && !parlRelevant) return null;
    return (
        <Stack gap="md">
            {hasPf && (
                <Lane
                    projectId={projectId}
                    track="PF"
                    label="Planfeststellung"
                    state={pfState}
                    documents={pfDocuments}
                    canEdit={canEdit}
                />
            )}
            {parlRelevant && (
                <Lane
                    projectId={projectId}
                    track="PARL"
                    label="Parlamentarische Befassung"
                    state={parlState}
                    documents={parlDocuments}
                    canEdit={canEdit}
                />
            )}
        </Stack>
    );
}
