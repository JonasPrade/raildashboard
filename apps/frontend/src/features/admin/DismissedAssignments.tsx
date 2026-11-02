/**
 * „Dauerhaft ignorieren“ on /admin/unassigned (feature-unassigned-assignments.md):
 * the per-row anchor with its confirm modal, and the section listing the
 * ignored records with „Wieder aufnehmen“.
 */

import { useState } from "react";
import {
    Anchor,
    Badge,
    Button,
    Collapse,
    Group,
    Modal,
    Stack,
    Table,
    Text,
    Textarea,
    Title,
    UnstyledButton,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { ChevronDown, ChevronRight, EyeOff } from "lucide-react";
import { ResponsiveTable } from "../../shared/ui/ResponsiveTable";
import { formatDate } from "../../shared/format";
import {
    useDismissAssignment,
    useDismissedAssignments,
    useRestoreAssignment,
    type AssignmentKind,
} from "../../shared/api/queries";

const KIND_LABEL: Record<AssignmentKind, string> = {
    finve: "FinVe",
    vib: "VIB",
    gvfg: "GVFG",
    infraplan: "Infraplan",
};

export type DismissTarget = { kind: AssignmentKind; entryId: number; label: string };

/** Small anchor under a row's assign controls. */
export function DismissAnchor({ onClick }: { onClick: () => void }) {
    return (
        <Anchor component="button" type="button" size="xs" c="dimmed" onClick={onClick}>
            <Group gap={2} wrap="nowrap" component="span">
                <EyeOff size={11} />
                Dauerhaft ignorieren
            </Group>
        </Anchor>
    );
}

/** Confirm with an optional reason; the row leaves the open list. */
export function DismissModal({ target, onClose }: { target: DismissTarget | null; onClose: () => void }) {
    const [note, setNote] = useState("");
    const dismiss = useDismissAssignment();

    const close = () => {
        setNote("");
        onClose();
    };

    const submit = async () => {
        if (!target) return;
        try {
            await dismiss.mutateAsync({ kind: target.kind, entryId: target.entryId, note: note.trim() || null });
            notifications.show({ color: "green", message: "Eintrag wird nicht mehr als offen geführt." });
            close();
        } catch {
            notifications.show({ color: "red", message: "Ignorieren fehlgeschlagen." });
        }
    };

    return (
        <Modal opened={target !== null} onClose={close} title="Dauerhaft ignorieren">
            <Stack gap="sm">
                <Text size="sm">
                    <b>{target ? KIND_LABEL[target.kind] : ""}</b>: {target?.label}
                </Text>
                <Text size="sm" c="dimmed">
                    Der Eintrag erscheint nicht mehr unter „Offene Zuordnungen“ und zählt nicht mehr im Zähler.
                    Er bleibt unverändert und lässt sich unten unter „Ignorierte Einträge“ wieder aufnehmen.
                </Text>
                <Textarea
                    label="Grund (optional)"
                    placeholder="z. B. kein Schienenprojekt, reine Ausrüstungsposition"
                    value={note}
                    onChange={(e) => setNote(e.currentTarget.value)}
                    autosize
                    minRows={2}
                />
                <Group justify="flex-end">
                    <Button variant="default" onClick={close}>
                        Abbrechen
                    </Button>
                    <Button onClick={submit} loading={dismiss.isPending}>
                        Ignorieren
                    </Button>
                </Group>
            </Stack>
        </Modal>
    );
}

/** Collapsed list of ignored records with „Wieder aufnehmen“. */
export function DismissedSection() {
    const [open, setOpen] = useState(false);
    const { data: dismissed } = useDismissedAssignments();
    const restore = useRestoreAssignment();

    const handleRestore = async (kind: AssignmentKind, entryId: number) => {
        try {
            await restore.mutateAsync({ kind, entryId });
            notifications.show({ color: "green", message: "Eintrag ist wieder offen." });
        } catch {
            notifications.show({ color: "red", message: "Wiederaufnahme fehlgeschlagen." });
        }
    };

    const count = dismissed?.length ?? 0;

    return (
        <Stack gap="sm">
            <UnstyledButton onClick={() => setOpen((o) => !o)} aria-expanded={open}>
                <Group className="idt-section-head" gap="xs" align="center">
                    {open ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                    <Title order={2} className="idt-title-plain">
                        Ignorierte Einträge
                    </Title>
                    <Badge variant="outline">{dismissed ? count : "…"}</Badge>
                </Group>
            </UnstyledButton>
            <Collapse in={open}>
                <ResponsiveTable minWidth={720} withTableBorder withColumnBorders>
                    <Table.Thead>
                        <Table.Tr>
                            <Table.Th>Quelle</Table.Th>
                            <Table.Th>Eintrag</Table.Th>
                            <Table.Th>Grund</Table.Th>
                            <Table.Th>Ignoriert</Table.Th>
                            <Table.Th />
                        </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                        {count === 0 && (
                            <Table.Tr>
                                <Table.Td colSpan={5}>
                                    <Text c="dimmed" size="sm" ta="center">Keine ignorierten Einträge.</Text>
                                </Table.Td>
                            </Table.Tr>
                        )}
                        {(dismissed ?? []).map((d) => (
                            <Table.Tr key={`${d.kind}-${d.entry_id}`}>
                                <Table.Td>
                                    <Badge variant="outline">{KIND_LABEL[d.kind]}</Badge>
                                </Table.Td>
                                <Table.Td style={{ maxWidth: 320 }}>
                                    {d.label}
                                    {d.detail && <Text size="xs" c="dimmed">{d.detail}</Text>}
                                </Table.Td>
                                <Table.Td style={{ maxWidth: 260 }}>
                                    <Text size="sm">{d.note || "–"}</Text>
                                </Table.Td>
                                <Table.Td style={{ whiteSpace: "nowrap" }}>
                                    <Text size="sm">{formatDate(d.dismissed_at)}</Text>
                                    {d.dismissed_by && <Text size="xs" c="dimmed">{d.dismissed_by}</Text>}
                                </Table.Td>
                                <Table.Td>
                                    <Button
                                        size="xs"
                                        variant="light"
                                        loading={restore.isPending && restore.variables?.entryId === d.entry_id
                                            && restore.variables?.kind === d.kind}
                                        onClick={() => handleRestore(d.kind, d.entry_id)}
                                    >
                                        Wieder aufnehmen
                                    </Button>
                                </Table.Td>
                            </Table.Tr>
                        ))}
                    </Table.Tbody>
                </ResponsiveTable>
            </Collapse>
        </Stack>
    );
}
