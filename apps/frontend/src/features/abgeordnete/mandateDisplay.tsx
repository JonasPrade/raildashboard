/**
 * Shared presentation of a mandate.
 *
 * The whole feature rests on one distinction, so it is made once here: a direct
 * mandate is what the source reports as ``mandate_won == "constituency"``.
 * Everyone else with a constituency ran there and entered over the state list —
 * a weaker statement, and it has to keep reading as one.
 */
import { Anchor, Badge, Group, Stack, Text } from "@mantine/core";

import type { Mandate } from "../../shared/api/queries";

export const COMMITTEE_LABELS: Record<string, string> = {
    verkehr: "Verkehrsausschuss",
    haushalt: "Haushaltsausschuss",
};

export const COMMITTEE_SHORT: Record<string, string> = {
    verkehr: "Verkehr",
    haushalt: "Haushalt",
};

/** Kilometres, or the honest "no kilometres here" for a point geometry. */
export function formatWeight(lengthKm: number, overlapKind: string): string {
    if (overlapKind === "point") return "Lage im Wahlkreis";
    if (lengthKm >= 10) return `${lengthKm.toLocaleString("de-DE", { maximumFractionDigits: 0 })} km`;
    return `${lengthKm.toLocaleString("de-DE", { maximumFractionDigits: 1 })} km`;
}

export function formatShare(share: number): string {
    return `${(share * 100).toLocaleString("de-DE", { maximumFractionDigits: 0 })} %`;
}

export function CommitteeBadges({ committees }: { committees: Mandate["committees"] }) {
    if (committees.length === 0) return null;
    return (
        <Group gap={6}>
            {committees.map((committee) => (
                <Badge key={committee.key} color="gold" variant="filled" size="sm">
                    {COMMITTEE_SHORT[committee.key] ?? committee.label}
                    {committee.role_label ? ` · ${committee.role_label}` : ""}
                </Badge>
            ))}
        </Group>
    );
}

export function MandateRow({ mandate }: { mandate: Mandate }) {
    return (
        <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm">
            <Stack gap={2}>
                <Group gap="xs">
                    {mandate.profile_url ? (
                        <Anchor
                            href={mandate.profile_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            fw={600}
                        >
                            {mandate.name}
                        </Anchor>
                    ) : (
                        <Text fw={600}>{mandate.name}</Text>
                    )}
                    {mandate.fraction && (
                        <Text size="sm" c="dimmed">
                            {mandate.fraction}
                        </Text>
                    )}
                </Group>
                {mandate.mandate_type === "moved_up" && (
                    <Text size="xs" c="dimmed">
                        nachgerückt
                    </Text>
                )}
            </Stack>
            <CommitteeBadges committees={mandate.committees} />
        </Group>
    );
}

export function MandateGroup({
    title,
    hint,
    mandates,
    emptyText,
}: {
    title: string;
    hint?: string;
    mandates: Mandate[];
    emptyText?: string;
}) {
    return (
        <Stack gap={6}>
            <Group gap="xs" align="baseline">
                <Text size="sm" fw={700} tt="uppercase" c="dimmed">
                    {title}
                </Text>
                {hint && (
                    <Text size="xs" c="dimmed">
                        {hint}
                    </Text>
                )}
            </Group>
            {mandates.length === 0 ? (
                <Text size="sm" c="dimmed" fs="italic">
                    {emptyText ?? "—"}
                </Text>
            ) : (
                mandates.map((mandate) => <MandateRow key={mandate.mandate_id} mandate={mandate} />)
            )}
        </Stack>
    );
}
