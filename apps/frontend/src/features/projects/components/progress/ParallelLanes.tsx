import { Group, Stack, Text } from "@mantine/core";
import { Check } from "lucide-react";

import { PARALLEL_STATE_LABEL, type ParallelState } from "./phaseMeta";
import { formatDate } from "../../../../shared/format";
import { LANE_STATE_COLOR } from "../../../../shared/theme/semanticColors";
import { SwatchTag } from "../../../../shared/ui/SwatchTag";
import { ExternalLinkButton } from "../../../../shared/ui/ExternalLinkButton";

type Link = { url: string; comment?: string | null };

const STATE_COLOR: Record<ParallelState, string> = {
    OFFEN: LANE_STATE_COLOR.idle,
    LAEUFT: LANE_STATE_COLOR.active,
    ABGESCHLOSSEN: LANE_STATE_COLOR.done,
};

function Lane({
    label,
    state,
    date,
    text,
    links,
    hideState = false,
}: {
    label: string;
    state: ParallelState | null;
    date?: string | null;
    text?: string | null;
    links: Link[];
    /** Suppress the state badge + date (the stepper milestone already shows them). */
    hideState?: boolean;
}) {
    const formattedDate = date ? formatDate(date) : null;
    const validLinks = links.filter((l) => l.url?.trim());

    return (
        <Stack gap={6}>
            <Group gap="sm" align="center" wrap="wrap">
                <Text size="sm" fw={600} style={{ minWidth: 190 }}>
                    {label}
                </Text>
                {!hideState && (
                    <SwatchTag color={state ? STATE_COLOR[state] : LANE_STATE_COLOR.idle}>
                        <Group gap={4} wrap="nowrap" component="span">
                            {state ? PARALLEL_STATE_LABEL[state] : "–"}
                            {state === "ABGESCHLOSSEN" && <Check size={12} aria-hidden />}
                        </Group>
                    </SwatchTag>
                )}
                {!hideState && formattedDate && (
                    <Text size="xs" c="dimmed">
                        {formattedDate}
                    </Text>
                )}
            </Group>

            {(validLinks.length > 0 || text) && (
                <Stack gap={6} pl={8}>
                    {validLinks.map((l, i) => (
                        <ExternalLinkButton key={i} url={l.url} label={l.comment?.trim() || undefined} />
                    ))}
                    {text && (
                        <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                            {text}
                        </Text>
                    )}
                </Stack>
            )}
        </Stack>
    );
}

type Props = {
    hasPf: boolean;
    pfState: ParallelState | null;
    parlRelevant: boolean;
    parlState: ParallelState | null;
    parlText?: string | null;
    parlDrucksacheUrl?: string | null;
    parlDate?: string | null;
    pfText?: string | null;
    /** Commented reference links for the Planfeststellung. */
    pfLinks?: Link[];
    pfDate?: string | null;
    /** True when the stepper already renders the PF milestone (state + date), so the
     * PF lane drops its redundant state badge and only stays for links / note. */
    pfStateInGraphic?: boolean;
    /** Same as pfStateInGraphic, for the parl. Befassung milestone. */
    parlStateInGraphic?: boolean;
};

export default function ParallelLanes({
    hasPf,
    pfState,
    parlRelevant,
    parlState,
    parlText = null,
    parlDrucksacheUrl = null,
    parlDate = null,
    pfText = null,
    pfLinks = [],
    pfDate = null,
    pfStateInGraphic = false,
    parlStateInGraphic = false,
}: Props) {
    // Beyond the state/date (which the milestone shows), does the lane carry
    // anything worth a row? If not — and the milestone covers it — drop the lane.
    const pfHasExtras = pfLinks.some((l) => l.url?.trim()) || !!pfText;
    const showPfLane = hasPf && (!pfStateInGraphic || pfHasExtras);

    // parl. Befassung keeps a single DIP (Drucksache) link.
    const parlLinks: Link[] = parlDrucksacheUrl
        ? [{ url: parlDrucksacheUrl, comment: "Bundestagsdrucksache (DIP)" }]
        : [];
    const parlHasExtras = parlLinks.length > 0 || !!parlText;
    const showParlLane = parlRelevant && (!parlStateInGraphic || parlHasExtras);

    if (!showPfLane && !showParlLane) return null;
    return (
        <Stack gap="md">
            {showPfLane && (
                <Lane
                    label="Planfeststellung"
                    state={pfState}
                    date={pfDate}
                    text={pfText}
                    links={pfLinks}
                    hideState={pfStateInGraphic}
                />
            )}
            {showParlLane && (
                <Lane
                    label="Parlamentarische Befassung"
                    state={parlState}
                    date={parlDate}
                    text={parlText}
                    links={parlLinks}
                    hideState={parlStateInGraphic}
                />
            )}
        </Stack>
    );
}
