import { useState } from "react";
import { Badge, Button, Group, Stack, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
    useDeleteGuideOverride,
    useSaveGuideOverride,
    type GuideOverride,
} from "../../shared/api/queries";
import GuideMarkdown from "./GuideMarkdown";

/**
 * One editable guide section: renders the effective markdown (server override
 * wins over the bundled default) and, for users with "guides.edit", an inline
 * markdown editor with save / cancel / reset-to-default.
 */
export default function GuideSectionBody({
    guideSlug,
    sectionKey,
    defaultBody,
    override,
    canEdit,
    dimmed,
}: {
    guideSlug: string;
    sectionKey: string;
    defaultBody: string;
    override: GuideOverride | undefined;
    canEdit: boolean;
    dimmed?: boolean;
}) {
    const [editing, setEditing] = useState(false);
    const [draft, setDraft] = useState("");
    const save = useSaveGuideOverride();
    const reset = useDeleteGuideOverride();

    const effective = override?.body_markdown ?? defaultBody;

    const handleSave = () => {
        save.mutate(
            { guideSlug, sectionKey, bodyMarkdown: draft },
            {
                onSuccess: () => setEditing(false),
                onError: () =>
                    notifications.show({
                        color: "red",
                        message: "Abschnitt konnte nicht gespeichert werden.",
                    }),
            },
        );
    };

    const handleReset = () => {
        reset.mutate(
            { guideSlug, sectionKey },
            {
                onSuccess: () => setEditing(false),
                onError: () =>
                    notifications.show({
                        color: "red",
                        message: "Zurücksetzen fehlgeschlagen.",
                    }),
            },
        );
    };

    if (editing) {
        return (
            <Stack gap="xs">
                <Textarea
                    value={draft}
                    onChange={(e) => setDraft(e.currentTarget.value)}
                    autosize
                    minRows={6}
                    maxRows={24}
                    styles={{ input: { fontFamily: "var(--mantine-font-family-monospace)", fontSize: 13 } }}
                />
                <Text size="xs" c="dimmed">
                    Markdown: **fett**, - Liste, [Link](/interner/pfad), `Chip`, Hinweisbox:
                    {" "}&gt; [!yellow] Titel — Farben: blue, yellow, green, red.
                </Text>
                <Group gap="xs">
                    <Button size="xs" onClick={handleSave} loading={save.isPending} disabled={!draft.trim()}>
                        Speichern
                    </Button>
                    <Button size="xs" variant="subtle" onClick={() => setEditing(false)}>
                        Abbrechen
                    </Button>
                    {override && (
                        <Button
                            size="xs"
                            variant="subtle"
                            color="red"
                            onClick={handleReset}
                            loading={reset.isPending}
                        >
                            Auf Standardtext zurücksetzen
                        </Button>
                    )}
                </Group>
            </Stack>
        );
    }

    return (
        <Stack gap={4}>
            <GuideMarkdown text={effective} dimmed={dimmed} />
            {canEdit && (
                <Group gap="xs">
                    <Button
                        size="compact-xs"
                        variant="subtle"
                        color="gray"
                        onClick={() => {
                            setDraft(effective);
                            setEditing(true);
                        }}
                    >
                        Bearbeiten
                    </Button>
                    {override && (
                        <Badge
                            size="xs"
                            variant="light"
                            color="grape"
                            title={
                                override.username_snapshot
                                    ? `Angepasst von ${override.username_snapshot}`
                                    : "Vom Standardtext abweichend"
                            }
                        >
                            angepasst
                        </Badge>
                    )}
                </Group>
            )}
        </Stack>
    );
}
