import { Anchor, Group, Paper, Stack, Text, Title } from "@mantine/core";
import { type ProjectBauportalEntry, useProjectBauportal } from "../../../shared/api/queries";
import { formatDate } from "../../../shared/format";
import { bauportalLinkedEntries } from "./bauportalEntries";

// ---------------------------------------------------------------------------
// DB-Bauportal on the project page (docs/features/feature-project-progress.md →
// „DB-Bauportal (#47)“ → „Anzeige auf der Projektseite“). Only confirmed
// entries with a link are shown; without one there is no card at all.
// ---------------------------------------------------------------------------

/** „Stand“ = the last nightly fetch that returned the entry (feature-routine-abrufe.md);
 *  an older backend only sends fetched_at. */
function stand(e: ProjectBauportalEntry): string | null {
    return e.last_seen_at ?? e.fetched_at ?? null;
}

export default function BauportalSection({ projectId }: { projectId: number }) {
    const { data } = useProjectBauportal(projectId);
    const entries = bauportalLinkedEntries(data);
    if (entries.length === 0) return null;

    return (
        <Paper withBorder p="var(--card-pad)">
            <Stack gap="md">
                <Title order={2} className="idt-title-plain">DB-Bauportal</Title>
                {entries.map((e) => (
                    <Stack key={e.id} gap={2} data-testid="bauportal-entry">
                        <Anchor
                            href={e.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            fw={600}
                            style={{ overflowWrap: "anywhere" }}
                        >
                            {e.shorttitle}
                        </Anchor>
                        <Group gap="md" wrap="wrap">
                            {e.status_raw && <Text size="sm">{e.status_raw}</Text>}
                            {e.projecttime_raw && (
                                <Text size="sm" c="dimmed">Bauzeit: {e.projecttime_raw}</Text>
                            )}
                        </Group>
                        {stand(e) && <Text size="xs" c="dimmed">Stand: {formatDate(stand(e) as string)}</Text>}
                    </Stack>
                ))}
            </Stack>
        </Paper>
    );
}
