import { Alert, Badge, Group, Stack, Text, ThemeIcon, Timeline } from "@mantine/core";
import { IconAlertTriangle, IconClockHour4, IconFlag } from "@tabler/icons-react";

import type { ProgressForecast } from "../../../../shared/api/queries";
import { formatMio } from "../../../gvfg/gvfgFormat";
import { MAIN_PHASE_LABEL, MILESTONE_LABEL, type MainPhase } from "./phaseMeta";

const SOURCE_COLOR: Record<string, string> = {
    "VIB-PFA": "blue",
    "Fulda-Runde": "grape",
    BVWP: "teal",
    "Schätzung": "gray",
};

function formatExpected(dateStr: string | null | undefined): string {
    if (!dateStr) return "Termin offen";
    const d = new Date(dateStr);
    if (Number.isNaN(d.getTime())) return "Termin offen";
    // Dates are period approximations → show month/year only.
    return `voraussichtlich ${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}

type IbnDoubt = NonNullable<ProgressForecast["ibn_doubt"]>;

/** The GVFG-Finanzreihe still funds the project after its known commissioning. */
function IbnDoubtAlert({ doubt }: { doubt: IbnDoubt }) {
    const share = doubt.aid_total > 0 ? Math.round((doubt.aid_after / doubt.aid_total) * 100) : null;
    const years = doubt.periods.map((p) => `${p.label}: ${formatMio(p.aid)}`).join(" · ");
    return (
        <Alert color="gold" variant="light" icon={<IconAlertTriangle size={16} />} title={`Inbetriebnahme ${doubt.ibn_year} fraglich`}>
            <Text size="sm">
                Die GVFG-Finanzreihe (Ausgabe {doubt.edition}, Abschnitt GVFG) sieht nach {doubt.ibn_year} noch {formatMio(doubt.aid_after)} Mio. € Finanzhilfen vor
                {share !== null && ` (${share} % der Finanzhilfen)`}. Quelle des Inbetriebnahmejahrs:{" "}
                {doubt.ibn_source.startsWith("GVFG") ? `${doubt.ibn_source} (Inbetriebnahme gepl.)` : doubt.ibn_source}.
            </Text>
            {years && (
                <Text size="xs" c="dimmed" mt={4}>
                    {years} (Mio. €)
                </Text>
            )}
        </Alert>
    );
}

export default function ForecastPanel({
    forecast,
}: {
    forecast: ProgressForecast | null | undefined;
}) {
    if (!forecast || !forecast.has_data) {
        return (
            <Stack gap="sm">
                <Text size="sm" c="dimmed">
                    Keine Prognosedaten verfügbar (weder BVWP-Dauern noch VIB-/Fulda-Termine).
                </Text>
                {forecast?.ibn_doubt && <IbnDoubtAlert doubt={forecast.ibn_doubt} />}
            </Stack>
        );
    }

    return (
        <Stack gap="sm">
            {forecast.remaining_text && (
                <Group gap="xs">
                    <ThemeIcon variant="light" size="sm" color="indigo">
                        <IconClockHour4 size={14} />
                    </ThemeIcon>
                    <Text size="sm" fw={600}>
                        {forecast.remaining_text}
                    </Text>
                </Group>
            )}

            {forecast.next_steps.length > 0 ? (
                <Timeline active={-1} bulletSize={18} lineWidth={2}>
                    {forecast.next_steps.map((step) => (
                        <Timeline.Item
                            key={step.phase}
                            bullet={<IconFlag size={11} />}
                            title={
                                <Group gap="xs">
                                    <Text size="sm" fw={600}>
                                        {MILESTONE_LABEL[step.phase as MainPhase] ?? step.phase}
                                    </Text>
                                    <Badge size="xs" variant="light" color={SOURCE_COLOR[step.source] ?? "gray"}>
                                        {step.source}
                                    </Badge>
                                </Group>
                            }
                        >
                            <Text size="xs" c="dimmed">
                                {MAIN_PHASE_LABEL[step.phase as MainPhase] ?? step.phase} ·{" "}
                                {formatExpected(step.expected_date)}
                            </Text>
                        </Timeline.Item>
                    ))}
                </Timeline>
            ) : (
                <Text size="sm" c="dimmed">
                    Projekt hat die letzte erfasste Phase erreicht.
                </Text>
            )}

            {forecast.ibn_doubt && <IbnDoubtAlert doubt={forecast.ibn_doubt} />}
        </Stack>
    );
}
