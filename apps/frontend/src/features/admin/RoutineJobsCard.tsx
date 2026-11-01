/**
 * Block „Zeitgesteuerte Abrufe“ in /admin/system (feature-routine-abrufe.md, E3).
 *
 * One entry per routine job: timetable, next slot, last run (time, trigger
 * „Zeitplan“ or user, duration), status and the error text. Cards instead of a
 * table so the block stays readable at 360 px.
 */

import { Alert, Anchor, Badge, Group, Paper, SimpleGrid, Stack, Text } from "@mantine/core";
import { Link } from "react-router-dom";

import { useRoutineJobs, type RoutineJobStatus } from "../../shared/api/queries";
import { LoadingState } from "../../shared/ui/LoadingState";
import { StatusTag } from "../../shared/ui/SwatchTag";
import {
    RUN_STATUS_TONE,
    formatBerlin,
    formatDuration,
    runStatusLabel,
    triggerLabel,
} from "./routineJobs";

function attentionReason(job: RoutineJobStatus): string | null {
    if (job.last_run?.status === "error") return "Letzter Lauf fehlgeschlagen";
    if (job.overdue) {
        return job.last_success_at
            ? "Länger als das doppelte Intervall kein erfolgreicher Lauf"
            : "Noch kein erfolgreicher Lauf";
    }
    return null;
}

function JobEntry({ job }: { job: RoutineJobStatus }) {
    const run = job.last_run;
    const reason = attentionReason(job);
    return (
        <Paper withBorder p="sm" data-testid={`routine-job-${job.key}`}>
            <Stack gap={6}>
                <Group justify="space-between" gap="xs" wrap="wrap">
                    <Text fw={600} size="sm">{job.label}</Text>
                    {run ? (
                        <StatusTag size="xs" tone={RUN_STATUS_TONE[run.status] ?? "neutral"}>
                            {runStatusLabel(run)}
                        </StatusTag>
                    ) : (
                        <StatusTag size="xs" tone="neutral">noch kein Lauf</StatusTag>
                    )}
                </Group>
                <Text size="xs" c="dimmed">
                    {job.schedule_label}
                    {job.next_run_at ? ` · nächster Termin ${formatBerlin(job.next_run_at)}` : ""}
                </Text>
                {job.running_since && (
                    <Text size="sm">Läuft gerade seit {formatBerlin(job.running_since)}</Text>
                )}
                {run && (
                    <Text size="sm">
                        Letzter Lauf: {formatBerlin(run.started_at)} · {triggerLabel(run)} · Dauer{" "}
                        {formatDuration(run.duration_seconds)}
                    </Text>
                )}
                {run?.error && (run.status === "error" || run.status === "skipped" || run.status === "running") && (
                    <Text size="xs" c={run.status === "error" ? "red" : "dimmed"} style={{ overflowWrap: "anywhere" }}>
                        {run.error}
                    </Text>
                )}
                {job.last_success_at && run?.status !== "success" && (
                    <Text size="xs" c="dimmed">
                        Letzter erfolgreicher Lauf: {formatBerlin(job.last_success_at)}
                    </Text>
                )}
                {reason && (
                    <Badge color="red" variant="light" size="sm" style={{ alignSelf: "flex-start" }}>
                        {reason}
                    </Badge>
                )}
                <Anchor component={Link} to={job.admin_path} size="sm">
                    {job.admin_label} →
                </Anchor>
            </Stack>
        </Paper>
    );
}

export default function RoutineJobsCard() {
    const { data, isLoading, isError } = useRoutineJobs();

    return (
        <Paper withBorder p="var(--card-pad)">
            <Stack gap="md">
                <Group justify="space-between" gap="xs" wrap="wrap">
                    <Text fw={600} size="md">Zeitgesteuerte Abrufe</Text>
                    {data && (
                        <Badge
                            color={data.needs_attention ? "red" : "teal"}
                            variant={data.needs_attention ? "filled" : "light"}
                        >
                            {!data.enabled
                                ? "Zeitplan abgeschaltet"
                                : data.needs_attention
                                  ? "Bitte prüfen"
                                  : "Alles im Plan"}
                        </Badge>
                    )}
                </Group>
                <Text size="sm" c="dimmed">
                    Routine-Abrufe startet der Dienst <b>scheduler</b> (Celery Beat) nachts von selbst
                    (Zeiten in deutscher Zeit, vor der Datensicherung um 04:05 Uhr). Ein verpasster
                    Termin wird nicht nachgeholt; der nächste greift. Von Hand startet man einen Job auf
                    der jeweiligen Fachseite.
                </Text>

                {isLoading && <LoadingState rows={3} label="Zeitplan wird geladen …" />}
                {isError && (
                    <Alert color="red" variant="light" title="Zeitplan nicht abrufbar">
                        Der Stand der zeitgesteuerten Abrufe konnte nicht geladen werden.
                    </Alert>
                )}

                {data && !data.enabled && (
                    <Alert color="red" variant="light" title="Zeitplan abgeschaltet (Env)">
                        <Text size="sm">
                            <code>ROUTINE_JOBS_ENABLED=false</code> — der Scheduler reiht nichts ein. Die
                            Knöpfe auf den Fachseiten funktionieren weiter.
                        </Text>
                    </Alert>
                )}

                {data && (
                    <SimpleGrid cols={{ base: 1, md: 3 }} spacing="sm">
                        {data.jobs.map((job) => (
                            <JobEntry key={job.key} job={job} />
                        ))}
                    </SimpleGrid>
                )}

                <Text size="xs" c="dimmed">
                    Steht der Scheduler, gibt es keinen Lauf — dann erscheint hier und in der
                    Admin-Übersicht ein Hinweis. Auf dem Server: <code>docker compose ps scheduler</code>,{" "}
                    <code>docker compose logs --tail=50 scheduler</code>.
                </Text>
            </Stack>
        </Paper>
    );
}
