/**
 * Shared building blocks of the import-review features (Bauportal, Medien,
 * Fulda, Haushalt, VIB): the per-row patch helper with error toast, the
 * confirm badge cluster, the "Projekt fehlt?" draft-project anchor, the
 * only-unconfirmed filter switch and the upload→Celery-poll state machine.
 */

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
    Alert,
    Anchor,
    Badge,
    Button,
    Group,
    Loader,
    Progress,
    Stack,
    Switch,
    Text,
    Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconCheck, IconPlus } from "@tabler/icons-react";
import type { UseMutationResult } from "@tanstack/react-query";

import {
    useTaskStatus,
    type Project,
    type TaskProgressMeta,
} from "../../../shared/api/queries";
import CreateDraftProjectModal from "../../projects/CreateDraftProjectModal";

// ---------------------------------------------------------------------------
// Per-row PATCH with error toast
// ---------------------------------------------------------------------------

export function usePatchWithToast<TData, TError, TPatch, TContext>(
    mutation: UseMutationResult<TData, TError, { entryId: number; data: TPatch }, TContext>,
    entryId: number,
) {
    return (data: TPatch) =>
        mutation.mutate(
            { entryId, data },
            {
                onError: () =>
                    notifications.show({
                        color: "red",
                        title: "Fehler",
                        message: "Die Änderung konnte nicht gespeichert werden.",
                    }),
            },
        );
}

// ---------------------------------------------------------------------------
// Confirm badge + saving indicator cluster
// ---------------------------------------------------------------------------

/**
 * Three visually distinct states so the pending action is obvious:
 * assigned-but-unconfirmed renders an actual „Übernehmen"-button instead of a
 * badge that merely reads „offen".
 */
export function ConfirmBadge({
    confirmed,
    canConfirm,
    onToggle,
    confirmTitle = "Zuordnung übernehmen",
    revokeTitle = "Übernahme zurücknehmen",
    blockedTitle = "Erst ein Projekt zuordnen",
}: {
    confirmed: boolean;
    canConfirm: boolean;
    onToggle: () => void;
    confirmTitle?: string;
    revokeTitle?: string;
    blockedTitle?: string;
}) {
    if (confirmed) {
        return (
            <Badge
                variant="light"
                color="green"
                style={{ cursor: "pointer" }}
                onClick={onToggle}
                title={revokeTitle}
            >
                aktiv
            </Badge>
        );
    }

    if (canConfirm) {
        return (
            <Button
                size="compact-xs"
                color="blue"
                leftSection={<IconCheck size={13} />}
                onClick={onToggle}
                title={confirmTitle}
            >
                Übernehmen
            </Button>
        );
    }

    return (
        <Badge variant="light" color="gray" style={{ cursor: "not-allowed" }} title={blockedTitle}>
            offen
        </Badge>
    );
}

export function SavingIndicator() {
    return (
        <Tooltip label="Wird gespeichert …" withArrow>
            <Loader size={14} />
        </Tooltip>
    );
}

// ---------------------------------------------------------------------------
// "Projekt fehlt?" anchor (+ optional self-managed draft-project modal)
// ---------------------------------------------------------------------------

type MissingProjectAnchorProps =
    | {
          /** Lifted-modal variant: the page owns the CreateDraftProjectModal. */
          onClick: () => void;
          alignSelfStart?: boolean;
      }
    | {
          /** Self-managed variant: the anchor renders its own modal. */
          initialName?: string;
          sourceLabel: string;
          onCreated: (project: Project) => void;
          alignSelfStart?: boolean;
      };

export function MissingProjectAnchor(props: MissingProjectAnchorProps) {
    const [open, setOpen] = useState(false);
    const selfManaged = !("onClick" in props);

    return (
        <>
            <Anchor
                component="button"
                type="button"
                size="xs"
                style={props.alignSelfStart ? { alignSelf: "flex-start" } : undefined}
                onClick={() => ("onClick" in props ? props.onClick() : setOpen(true))}
            >
                <Group gap={2} wrap="nowrap" component="span">
                    <IconPlus size={11} />
                    Projekt fehlt?
                </Group>
            </Anchor>
            {selfManaged && (
                <CreateDraftProjectModal
                    opened={open}
                    onClose={() => setOpen(false)}
                    initialName={props.initialName}
                    sourceLabel={props.sourceLabel}
                    onCreated={props.onCreated}
                />
            )}
        </>
    );
}

// ---------------------------------------------------------------------------
// "Nur offene (unbestätigt)" filter switch
// ---------------------------------------------------------------------------

export function UnconfirmedFilter({
    checked,
    onChange,
}: {
    checked: boolean;
    onChange: (checked: boolean) => void;
}) {
    return (
        <Switch
            label="Nur offene (unbestätigt)"
            checked={checked}
            onChange={(e) => onChange(e.currentTarget.checked)}
        />
    );
}

// ---------------------------------------------------------------------------
// Upload → Celery poll → navigate state machine
// ---------------------------------------------------------------------------

/**
 * A job still unstarted after this long is not merely queued — most likely no
 * worker is running. Long enough that a healthy stack never shows the warning,
 * short enough that nobody stares at a dead spinner for minutes.
 */
const STUCK_AFTER_MS = 12_000;

export function useImportTask({
    onSuccess,
    onFailure,
}: {
    /** Called once when the task reaches SUCCESS. */
    onSuccess: (result: unknown, taskId: string) => void;
    /** Optional custom FAILURE handling; default shows a red toast. */
    onFailure?: (error: string | null) => void;
}) {
    const [taskId, setTaskId] = useState<string | null>(null);
    const [startedAt, setStartedAt] = useState<number | null>(null);
    const taskStatus = useTaskStatus(taskId);

    useEffect(() => {
        if (!taskId || !taskStatus.data) return;
        const { status, result, hint } = taskStatus.data;
        if (status === "SUCCESS") {
            onSuccess(result, taskId);
        } else if (status === "FAILURE") {
            const error = taskStatus.data.error ?? null;
            setTaskId(null);
            setStartedAt(null);
            if (onFailure) {
                onFailure(error);
            } else {
                notifications.show({
                    color: "red",
                    title: "Parser-Fehler",
                    // The backend names the exception and where it was raised;
                    // the hint says where the full traceback is.
                    message: [error ?? "Unbekannter Fehler", hint].filter(Boolean).join(" "),
                    autoClose: false,
                });
            }
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [taskStatus.data, taskId]);

    const isRunning = taskId !== null && taskStatus.data?.status !== "SUCCESS";
    const progress =
        taskStatus.data?.status === "PROGRESS"
            ? (taskStatus.data.result as TaskProgressMeta | null)
            : null;

    // Why nothing is happening: the backend sets `hint` while a job waits
    // without a worker. Shown only after the grace period, because a healthy
    // worker needs a moment to pick the job up.
    const stuckFor = startedAt !== null && Date.now() - startedAt > STUCK_AFTER_MS;
    const warning =
        taskStatus.data?.status === "PENDING" && stuckFor
            ? taskStatus.data.hint ?? null
            : null;

    return {
        taskId,
        start: (id: string) => {
            setTaskId(id);
            setStartedAt(Date.now());
        },
        reset: () => {
            setTaskId(null);
            setStartedAt(null);
        },
        isRunning,
        progress,
        warning,
    };
}

function defaultProgressLabel(progress: TaskProgressMeta | null): string {
    if (progress?.step_label) return progress.step_label;
    if (progress?.current_page != null) {
        return `Seite ${progress.current_page} / ${progress.total_pages}`;
    }
    return "Parsing läuft…";
}

export function TaskProgressIndicator({
    progress,
    label,
    animated,
    warning,
}: {
    progress: TaskProgressMeta | null;
    /** Override the default step/page label. */
    label?: string;
    /** Override the default "animate while indeterminate" behavior. */
    animated?: boolean;
    /** Why the job has not started — from `useImportTask().warning`. */
    warning?: string | null;
}) {
    const value =
        progress?.current_page != null && progress?.total_pages != null
            ? Math.round((progress.current_page / progress.total_pages) * 100)
            : 100;
    return (
        <Stack gap={4}>
            <Group gap="xs">
                <Loader size="xs" />
                <Text size="sm">{label ?? defaultProgressLabel(progress)}</Text>
            </Group>
            <Progress value={value} animated={animated ?? !progress} size="sm" />
            {warning && (
                <Alert color="orange" variant="light" title="Der Auftrag wurde noch nicht gestartet">
                    <Stack gap={4}>
                        <Text size="sm">{warning}</Text>
                        <Anchor component={Link} to="/admin/system" size="sm">
                            Systemstatus öffnen →
                        </Anchor>
                    </Stack>
                </Alert>
            )}
        </Stack>
    );
}
