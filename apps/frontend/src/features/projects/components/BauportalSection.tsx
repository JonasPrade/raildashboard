import { Anchor, Group, Paper, Stack, Text, Title } from "@mantine/core";
import { useProjectBauportal } from "../../../shared/api/queries";
import { formatDate } from "../../../shared/format";
import { bauportalLinkedEntries } from "./bauportalEntries";

// ---------------------------------------------------------------------------
// DB-Bauportal on the project page (docs/features/feature-project-progress.md →
// „DB-Bauportal (#47)“ → „Anzeige auf der Projektseite“). Only confirmed
// entries with a link are shown; without one there is no card at all.
// ---------------------------------------------------------------------------

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
                        {e.fetched_at && (
                            <Text size="xs" c="dimmed">Stand: {formatDate(e.fetched_at)}</Text>
                        )}
                    </Stack>
                ))}
            </Stack>
        </Paper>
    );
}
