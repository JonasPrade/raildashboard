import { useState } from "react";
import {
    ActionIcon,
    Badge,
    Button,
    Divider,
    Drawer,
    Group,
    NumberInput,
    ScrollArea,
    Select,
    Stack,
    Switch,
    Table,
    Text,
    Textarea,
    TextInput,
    Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconPlus, IconRefresh, IconTrash } from "@tabler/icons-react";

import {
    type ProgressObservationCreate,
    type ProjectProgress,
    type ProjectProgressUpdate,
    useAddProgressObservation,
    useDeleteProgressObservation,
    useRecomputeProgress,
    useUpdateProjectProgress,
} from "../../../../shared/api/queries";
import {
    LIFECYCLE_LABEL,
    MAIN_PHASES,
    MAIN_PHASE_LABEL,
    PARALLEL_STATES,
    PARALLEL_STATE_LABEL,
    SOURCE_LABEL,
    TRACK_LABEL,
    formatTimestamp,
    stateLabel,
    type LifecycleStatus,
    type MainPhase,
    type ObservationTrack,
    type ParallelState,
    type SourceType,
} from "./phaseMeta";

const PHASE_NONE = "__none__";
const PARL_STATE_NONE = "__none__";
const MANUAL_SOURCE_TYPES: SourceType[] = ["MANUELL", "FULDA_RUNDE", "BAUPORTAL", "MEDIEN"];

type PfLinkDraft = { url: string; comment: string };

/** Trim, drop empty-URL rows, and collapse blank comments to null. */
function normPfLinks(links: PfLinkDraft[]): { url: string; comment: string | null }[] {
    return links
        .map((l) => ({ url: l.url.trim(), comment: l.comment.trim() }))
        .filter((l) => l.url !== "")
        .map((l) => ({ url: l.url, comment: l.comment || null }));
}

function serverPfLinks(progress: ProjectProgress): { url: string; comment: string | null }[] {
    return normPfLinks((progress.pf_links ?? []).map((l) => ({ url: l.url, comment: l.comment ?? "" })));
}

// All editable state is held locally and only flushed to the API on "Speichern".
type Draft = {
    phaseOverride: MainPhase | null; // null = computed (no override)
    overrideNote: string;
    lifecycle: LifecycleStatus;
    hasPf: boolean;
    parlOverride: boolean | null; // null = group standard
    // Planfeststellung + parliamentary involvement details.
    pfStateOverride: ParallelState | null; // null = no override ("Zustand")
    pfLinks: PfLinkDraft[]; // multiple commented reference links
    parlStateOverride: ParallelState | null; // null = no override ("Beschluss")
    parlText: string;
    parlDrucksacheUrl: string;
    parlDate: string; // ISO date or ""
    // Planfeststellung details.
    pfText: string;
    pfDate: string; // ISO date or ""
    newObservations: ProgressObservationCreate[];
    removedObservationIds: number[]; // existing manual observations to delete
};

function initDraft(progress: ProjectProgress): Draft {
    return {
        phaseOverride: progress.is_overridden ? (progress.effective_phase as MainPhase) : null,
        overrideNote: progress.manual_override_note ?? "",
        lifecycle: progress.lifecycle_status as LifecycleStatus,
        hasPf: progress.has_planfeststellung,
        parlOverride: progress.parl_befassung_relevant_override ?? null,
        pfStateOverride: (progress.pf_state_override as ParallelState | null) ?? null,
        parlStateOverride: (progress.parl_state_override as ParallelState | null) ?? null,
        parlText: progress.parl_befassung_text ?? "",
        parlDrucksacheUrl: progress.parl_drucksache_url ?? "",
        parlDate: progress.parl_befassung_date ?? "",
        pfText: progress.pf_text ?? "",
        pfLinks: (progress.pf_links ?? []).map((l) => ({ url: l.url, comment: l.comment ?? "" })),
        pfDate: progress.pf_date ?? "",
        newObservations: [],
        removedObservationIds: [],
    };
}

function isDirty(draft: Draft, progress: ProjectProgress): boolean {
    const currentOverride = progress.is_overridden
        ? (progress.effective_phase as MainPhase)
        : null;
    const currentParl = progress.parl_befassung_relevant_override ?? null;
    return (
        draft.phaseOverride !== currentOverride ||
        (draft.overrideNote || "") !== (progress.manual_override_note ?? "") ||
        draft.lifecycle !== progress.lifecycle_status ||
        draft.hasPf !== progress.has_planfeststellung ||
        draft.parlOverride !== currentParl ||
        draft.pfStateOverride !== ((progress.pf_state_override as ParallelState | null) ?? null) ||
        draft.parlStateOverride !== ((progress.parl_state_override as ParallelState | null) ?? null) ||
        (draft.parlText || "") !== (progress.parl_befassung_text ?? "") ||
        (draft.parlDrucksacheUrl || "") !== (progress.parl_drucksache_url ?? "") ||
        (draft.parlDate || "") !== (progress.parl_befassung_date ?? "") ||
        (draft.pfText || "") !== (progress.pf_text ?? "") ||
        JSON.stringify(normPfLinks(draft.pfLinks)) !== JSON.stringify(serverPfLinks(progress)) ||
        (draft.pfDate || "") !== (progress.pf_date ?? "") ||
        draft.newObservations.length > 0 ||
        draft.removedObservationIds.length > 0
    );
}

// Build the scalar PATCH payload from the diff between draft and server state.
function scalarPayload(draft: Draft, progress: ProjectProgress): ProjectProgressUpdate | null {
    const payload: ProjectProgressUpdate = {};
    const currentOverride = progress.is_overridden
        ? (progress.effective_phase as MainPhase)
        : null;
    if (draft.phaseOverride !== currentOverride) {
        if (draft.phaseOverride === null) payload.clear_phase_override = true;
        else payload.manual_phase_override = draft.phaseOverride;
    }
    if ((draft.overrideNote || "") !== (progress.manual_override_note ?? "")) {
        payload.manual_override_note = draft.overrideNote || null;
    }
    if (draft.lifecycle !== progress.lifecycle_status) {
        payload.lifecycle_status = draft.lifecycle;
    }
    if (draft.hasPf !== progress.has_planfeststellung) {
        payload.has_planfeststellung = draft.hasPf;
    }
    const currentParl = progress.parl_befassung_relevant_override ?? null;
    if (draft.parlOverride !== currentParl) {
        if (draft.parlOverride === null) payload.clear_parl_relevant = true;
        else payload.parl_befassung_relevant = draft.parlOverride;
    }
    const currentPfState = (progress.pf_state_override as ParallelState | null) ?? null;
    if (draft.pfStateOverride !== currentPfState) {
        if (draft.pfStateOverride === null) payload.clear_pf_state_override = true;
        else payload.pf_state_override = draft.pfStateOverride;
    }
    const currentParlState = (progress.parl_state_override as ParallelState | null) ?? null;
    if (draft.parlStateOverride !== currentParlState) {
        if (draft.parlStateOverride === null) payload.clear_parl_state_override = true;
        else payload.parl_state_override = draft.parlStateOverride;
    }
    if ((draft.parlText || "") !== (progress.parl_befassung_text ?? "")) {
        payload.parl_befassung_text = draft.parlText || null;
    }
    if ((draft.parlDrucksacheUrl || "") !== (progress.parl_drucksache_url ?? "")) {
        payload.parl_drucksache_url = draft.parlDrucksacheUrl || null;
    }
    if ((draft.parlDate || "") !== (progress.parl_befassung_date ?? "")) {
        payload.parl_befassung_date = draft.parlDate || null;
    }
    if ((draft.pfText || "") !== (progress.pf_text ?? "")) {
        payload.pf_text = draft.pfText || null;
    }
    const pfLinksPayload = normPfLinks(draft.pfLinks);
    if (JSON.stringify(pfLinksPayload) !== JSON.stringify(serverPfLinks(progress))) {
        payload.pf_links = pfLinksPayload;
    }
    if ((draft.pfDate || "") !== (progress.pf_date ?? "")) {
        payload.pf_date = draft.pfDate || null;
    }
    return Object.keys(payload).length > 0 ? payload : null;
}

// ---------------------------------------------------------------------------
// Pending-observation entry form (adds to the draft, no immediate API call)
// ---------------------------------------------------------------------------

function ObservationDraftForm({ onAdd }: { onAdd: (obs: ProgressObservationCreate) => void }) {
    const [sourceType, setSourceType] = useState<SourceType>("MANUELL");
    // Manual observations only ever record a Leistungsphase (MAIN track). The
    // Planfeststellung / parl. Befassung tracks are maintained in the "Verfahren"
    // section instead, so this form no longer offers a track selector.
    const [state, setState] = useState<string>("VORPLANUNG");
    const [date, setDate] = useState("");
    const [confidence, setConfidence] = useState<string>("");
    const [note, setNote] = useState("");
    // Expected (future) milestone vs. a reached state. Expected entries only feed
    // the forecast and never pull the current phase forward.
    const [isExpected, setIsExpected] = useState(false);

    const stateOptions = MAIN_PHASES.map((p) => ({ value: p, label: MAIN_PHASE_LABEL[p] }));

    const submit = () => {
        const conf = confidence.trim() === "" ? null : Number(confidence);
        onAdd({
            source_type: sourceType,
            track: "MAIN",
            asserted_state: state,
            observed_date: date || null,
            confidence: conf !== null && Number.isFinite(conf) ? conf : null,
            note: note || null,
            is_expected: isExpected,
        });
        setNote("");
        setDate("");
        setConfidence("");
    };

    return (
        <Stack gap="xs">
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
                    label="Leistungsphase"
                    value={state}
                    onChange={(v) => setState(v ?? stateOptions[0].value)}
                    data={stateOptions}
                    w={200}
                />
                <TextInput
                    size="xs"
                    type="date"
                    label={isExpected ? "Erwartetes Datum" : "Datum"}
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
                    disabled={isExpected}
                />
                <TextInput
                    size="xs"
                    label="Notiz / Quelle"
                    value={note}
                    onChange={(e) => setNote(e.currentTarget.value)}
                    w={200}
                />
                <Button size="xs" leftSection={<IconPlus size={14} />} onClick={submit}>
                    Hinzufügen
                </Button>
            </Group>
            <Switch
                size="xs"
                label="Erwarteter Termin (nur Prognose, ändert die aktuelle Phase nicht)"
                checked={isExpected}
                onChange={(e) => setIsExpected(e.currentTarget.checked)}
            />
        </Stack>
    );
}

// ---------------------------------------------------------------------------
// Document lane (draft-buffered link/unlink)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Drawer
// ---------------------------------------------------------------------------

type Props = {
    projectId: number;
    progress: ProjectProgress;
    opened: boolean;
    onClose: () => void;
};

export default function ProgressEditDrawer({ projectId, progress, opened, onClose }: Props) {
    const [draft, setDraft] = useState<Draft | null>(null);
    const [saving, setSaving] = useState(false);

    const update = useUpdateProjectProgress(projectId);
    const addObs = useAddProgressObservation(projectId);
    const delObs = useDeleteProgressObservation(projectId);
    const recompute = useRecomputeProgress(projectId);

    const active = draft ?? initDraft(progress);
    const dirty = isDirty(active, progress);

    const set = (patch: Partial<Draft>) => setDraft({ ...active, ...patch });

    function reset() {
        setDraft(null);
    }

    function handleClose() {
        if (dirty && !window.confirm("Ungespeicherte Änderungen verwerfen?")) return;
        reset();
        onClose();
    }

    async function handleSave() {
        setSaving(true);
        try {
            const payload = scalarPayload(active, progress);
            if (payload) await update.mutateAsync(payload);
            for (const id of active.removedObservationIds) await delObs.mutateAsync(id);
            for (const obs of active.newObservations) await addObs.mutateAsync(obs);
            notifications.show({ color: "green", message: "Planungsstand gespeichert." });
            reset();
            onClose();
        } catch {
            notifications.show({ color: "red", message: "Speichern fehlgeschlagen." });
        } finally {
            setSaving(false);
        }
    }

    const manualObservations = progress.observations.filter((o) => !o.is_derived);
    const visibleManual = manualObservations.filter(
        (o) => !active.removedObservationIds.includes(o.id),
    );

    // Effective parl. Befassung relevance: explicit override wins, else the
    // resolved (group-default) value from the server.
    const parlRelevant =
        active.parlOverride !== null ? active.parlOverride : progress.parl_befassung_relevant;

    return (
        <Drawer
            opened={opened}
            onClose={handleClose}
            title={
                <Stack gap={2}>
                    <Text fw={600} size="sm">
                        Planungsstand bearbeiten
                    </Text>
                    <Text size="xs" c="dimmed">
                        {progress.is_superior
                            ? "Übergeordnetes Projekt"
                            : `Aktuelle Phase: ${MAIN_PHASE_LABEL[progress.effective_phase as MainPhase]}`}
                    </Text>
                </Stack>
            }
            position="right"
            size="xl"
            scrollAreaComponent={ScrollArea.Autosize}
        >
            <Stack gap="xl">
                {/* 1 — Phase & Override */}
                <Stack gap="sm">
                    <Title order={5}>Phase & Übersteuerung</Title>
                    <Text size="xs" c="dimmed">
                        Berechnet: {MAIN_PHASE_LABEL[progress.computed_phase as MainPhase]} ·{" "}
                        {(progress.computed_confidence * 100).toFixed(0)} % Vertrauen
                    </Text>
                    <Group gap="lg" align="flex-end" wrap="wrap">
                        <Select
                            size="xs"
                            label="Phasen-Override"
                            w={220}
                            value={active.phaseOverride ?? PHASE_NONE}
                            data={[
                                { value: PHASE_NONE, label: "— berechnet —" },
                                ...MAIN_PHASES.map((p) => ({ value: p, label: MAIN_PHASE_LABEL[p] })),
                            ]}
                            onChange={(v) =>
                                set({
                                    phaseOverride:
                                        !v || v === PHASE_NONE ? null : (v as MainPhase),
                                })
                            }
                        />
                        <TextInput
                            size="xs"
                            label="Override-Notiz"
                            w={300}
                            value={active.overrideNote}
                            onChange={(e) => set({ overrideNote: e.currentTarget.value })}
                        />
                    </Group>
                </Stack>

                <Divider />

                {/* 2 — Lebenszyklus */}
                <Stack gap="sm">
                    <Title order={5}>Lebenszyklus</Title>
                    <Select
                        size="xs"
                        label="Lebenszyklus"
                        w={170}
                        value={active.lifecycle}
                        data={(["AKTIV", "PAUSIERT", "ABGEBROCHEN"] as LifecycleStatus[]).map(
                            (s) => ({ value: s, label: LIFECYCLE_LABEL[s] }),
                        )}
                        onChange={(v) => v && set({ lifecycle: v as LifecycleStatus })}
                    />
                </Stack>

                <Divider />

                {/* 3 — Verfahren (switch menu): Planfeststellung & parl. Befassung */}
                <Stack gap="md">
                    <Title order={5}>Verfahren</Title>
                    <Text size="xs" c="dimmed">
                        Schalte ein Verfahren ein, um seine Angaben zu erfassen. Planfeststellung und
                        parlamentarische Befassung werden hier gepflegt — nicht über manuelle Beobachtungen.
                    </Text>

                    {/* Planfeststellung */}
                    <Stack gap="sm">
                        <Switch
                            label="Planfeststellung"
                            checked={active.hasPf}
                            onChange={(e) => set({ hasPf: e.currentTarget.checked })}
                        />
                        {active.hasPf && (
                            <Stack gap="sm" pl="md">
                                <Group gap="lg" align="flex-end" wrap="wrap">
                                    <Select
                                        size="xs"
                                        label="Zustand"
                                        w={190}
                                        value={active.pfStateOverride ?? PARL_STATE_NONE}
                                        data={[
                                            { value: PARL_STATE_NONE, label: "— nicht gesetzt —" },
                                            ...PARALLEL_STATES.map((s) => ({
                                                value: s,
                                                label: PARALLEL_STATE_LABEL[s],
                                            })),
                                        ]}
                                        onChange={(v) =>
                                            set({
                                                pfStateOverride:
                                                    !v || v === PARL_STATE_NONE
                                                        ? null
                                                        : (v as ParallelState),
                                            })
                                        }
                                    />
                                    <TextInput
                                        size="xs"
                                        type="date"
                                        label="Datum"
                                        w={160}
                                        value={active.pfDate}
                                        onChange={(e) => set({ pfDate: e.currentTarget.value })}
                                    />
                                </Group>
                                <Textarea
                                    size="xs"
                                    label="Anmerkung"
                                    autosize
                                    minRows={2}
                                    maxRows={8}
                                    value={active.pfText}
                                    onChange={(e) => set({ pfText: e.currentTarget.value })}
                                />
                                <Text size="xs" c="dimmed" fw={600} mt={4}>
                                    Links
                                </Text>
                                {active.pfLinks.map((linkRow, i) => (
                                    <Group key={i} gap="xs" align="flex-end" wrap="nowrap">
                                        <TextInput
                                            size="xs"
                                            label={i === 0 ? "URL" : undefined}
                                            placeholder="https://…"
                                            style={{ flex: 1 }}
                                            value={linkRow.url}
                                            onChange={(e) =>
                                                set({
                                                    pfLinks: active.pfLinks.map((l, j) =>
                                                        j === i ? { ...l, url: e.currentTarget.value } : l,
                                                    ),
                                                })
                                            }
                                        />
                                        <TextInput
                                            size="xs"
                                            label={i === 0 ? "Kommentar" : undefined}
                                            placeholder="z. B. Planfeststellungsbeschluss"
                                            style={{ flex: 1 }}
                                            value={linkRow.comment}
                                            onChange={(e) =>
                                                set({
                                                    pfLinks: active.pfLinks.map((l, j) =>
                                                        j === i ? { ...l, comment: e.currentTarget.value } : l,
                                                    ),
                                                })
                                            }
                                        />
                                        <ActionIcon
                                            variant="subtle"
                                            color="red"
                                            size="lg"
                                            aria-label="Link entfernen"
                                            onClick={() =>
                                                set({ pfLinks: active.pfLinks.filter((_, j) => j !== i) })
                                            }
                                        >
                                            <IconTrash size={14} />
                                        </ActionIcon>
                                    </Group>
                                ))}
                                <Button
                                    variant="light"
                                    size="compact-xs"
                                    leftSection={<IconPlus size={14} />}
                                    style={{ alignSelf: "flex-start" }}
                                    onClick={() =>
                                        set({ pfLinks: [...active.pfLinks, { url: "", comment: "" }] })
                                    }
                                >
                                    Link hinzufügen
                                </Button>
                            </Stack>
                        )}
                    </Stack>

                    <Divider variant="dashed" />

                    {/* Parlamentarische Befassung */}
                    <Stack gap="sm">
                        <Group gap="sm" align="center">
                            <Switch
                                label="Parlamentarische Befassung"
                                checked={parlRelevant}
                                onChange={(e) => set({ parlOverride: e.currentTarget.checked })}
                            />
                            {active.parlOverride !== null && (
                                <Button
                                    variant="subtle"
                                    size="compact-xs"
                                    onClick={() => set({ parlOverride: null })}
                                >
                                    Auf Gruppen-Standard zurücksetzen
                                </Button>
                            )}
                        </Group>
                        {parlRelevant && (
                            <Stack gap="sm" pl="md">
                                <Group gap="lg" align="flex-end" wrap="wrap">
                                    <Select
                                        size="xs"
                                        label="Beschluss"
                                        w={190}
                                        value={active.parlStateOverride ?? PARL_STATE_NONE}
                                        data={[
                                            { value: PARL_STATE_NONE, label: "— nicht gesetzt —" },
                                            ...PARALLEL_STATES.map((s) => ({
                                                value: s,
                                                label: PARALLEL_STATE_LABEL[s],
                                            })),
                                        ]}
                                        onChange={(v) =>
                                            set({
                                                parlStateOverride:
                                                    !v || v === PARL_STATE_NONE
                                                        ? null
                                                        : (v as ParallelState),
                                            })
                                        }
                                    />
                                    <TextInput
                                        size="xs"
                                        type="date"
                                        label="Datum"
                                        w={160}
                                        value={active.parlDate}
                                        onChange={(e) => set({ parlDate: e.currentTarget.value })}
                                    />
                                </Group>
                                <TextInput
                                    size="xs"
                                    label="Link zur Bundestagsdrucksache"
                                    placeholder="https://dserver.bundestag.de/btd/…"
                                    value={active.parlDrucksacheUrl}
                                    onChange={(e) => set({ parlDrucksacheUrl: e.currentTarget.value })}
                                />
                                <Textarea
                                    size="xs"
                                    label="Anmerkung"
                                    autosize
                                    minRows={2}
                                    maxRows={8}
                                    value={active.parlText}
                                    onChange={(e) => set({ parlText: e.currentTarget.value })}
                                />
                            </Stack>
                        )}
                    </Stack>
                </Stack>

                <Divider />

                {/* 4 — Beobachtungen */}
                <Stack gap="sm">
                    <Title order={5}>Manuelle Beobachtungen</Title>
                    <ObservationDraftForm
                        onAdd={(obs) => set({ newObservations: [...active.newObservations, obs] })}
                    />
                    {(visibleManual.length > 0 || active.newObservations.length > 0) && (
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
                                    <Table.Th />
                                </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                                {visibleManual.map((obs) => (
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
                                        <Table.Td>
                                            <ActionIcon
                                                variant="subtle"
                                                color="red"
                                                size="sm"
                                                aria-label="Beobachtung löschen"
                                                onClick={() =>
                                                    set({
                                                        removedObservationIds: [
                                                            ...active.removedObservationIds,
                                                            obs.id,
                                                        ],
                                                    })
                                                }
                                            >
                                                <IconTrash size={14} />
                                            </ActionIcon>
                                        </Table.Td>
                                    </Table.Tr>
                                ))}
                                {active.newObservations.map((obs, i) => (
                                    <Table.Tr key={`new-${i}`}>
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
                                        <Table.Td>
                                            <Group gap={4}>
                                                <Text size="sm">{obs.note ?? ""}</Text>
                                                <Badge size="xs" color="blue" variant="light">
                                                    neu
                                                </Badge>
                                            </Group>
                                        </Table.Td>
                                        <Table.Td>
                                            <Text size="sm" c="dimmed">
                                                du (nach Speichern)
                                            </Text>
                                        </Table.Td>
                                        <Table.Td>
                                            <Text size="sm" c="dimmed">
                                                –
                                            </Text>
                                        </Table.Td>
                                        <Table.Td>
                                            <ActionIcon
                                                variant="subtle"
                                                color="red"
                                                size="sm"
                                                aria-label="Beobachtung verwerfen"
                                                onClick={() =>
                                                    set({
                                                        newObservations: active.newObservations.filter(
                                                            (_, j) => j !== i,
                                                        ),
                                                    })
                                                }
                                            >
                                                <IconTrash size={14} />
                                            </ActionIcon>
                                        </Table.Td>
                                    </Table.Tr>
                                ))}
                            </Table.Tbody>
                        </Table>
                    )}
                </Stack>

                <Divider />

                {/* Footer */}
                <Group justify="space-between">
                    <Button
                        variant="subtle"
                        size="xs"
                        leftSection={<IconRefresh size={14} />}
                        onClick={() => recompute.mutate()}
                        loading={recompute.isPending}
                    >
                        Aus Quellen neu berechnen
                    </Button>
                    <Group gap="sm">
                        <Button variant="default" onClick={handleClose}>
                            Abbrechen
                        </Button>
                        <Button onClick={handleSave} loading={saving} disabled={!dirty}>
                            Speichern
                        </Button>
                    </Group>
                </Group>
            </Stack>
        </Drawer>
    );
}
