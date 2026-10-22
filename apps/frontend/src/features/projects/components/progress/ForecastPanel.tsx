import { Alert, Group, Stack, Text, ThemeIcon, Timeline } from "@mantine/core";
import { TriangleAlert, Clock, Flag } from "lucide-react";

import type { ProgressForecast } from "../../../../shared/api/queries";
import { formatExpected } from "../../../../shared/datePrecision";
import { formatMio } from "../../../gvfg/gvfgFormat";
import { MAIN_PHASE_LABEL, MILESTONE_LABEL, type MainPhase } from "./phaseMeta";
import { FORECAST_SOURCE_COLOR } from "../../../../shared/theme/semanticColors";
import { SwatchTag } from "../../../../shared/ui/SwatchTag";

const SOURCE_COLOR: Record<string, string> = FORECAST_SOURCE_COLOR;
const SOURCE_FALLBACK_COLOR = "var(--idt-line-strong)";

type IbnDoubt = NonNullable<ProgressForecast["ibn_doubt"]>;

/** The GVFG-Finanzreihe still funds the project after its known commissioning. */
function IbnDoubtAlert({ doubt }: { doubt: IbnDoubt }) {
    const share = doubt.aid_total > 0 ? Math.round((doubt.aid_after / doubt.aid_total) * 100) : null;
    const years = doubt.periods.map((p) => `${p.label}: ${formatMio(p.aid)}`).join(" · ");
    return (
        <Alert color="teal" variant="light" icon={<TriangleAlert size={16} />} title={`Inbetriebnahme ${doubt.ibn_year} fraglich`}>
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
                    <ThemeIcon variant="light" size="sm" color="violet">
                        <Clock size={16} />
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
                            bullet={<Flag size={11} />}
                            title={
                                <Group gap="xs">
                                    <Text size="sm" fw={600}>
                                        {MILESTONE_LABEL[step.phase as MainPhase] ?? step.phase}
                                    </Text>
                                    <SwatchTag size="xs" color={SOURCE_COLOR[step.source] ?? SOURCE_FALLBACK_COLOR}>
                                        {step.source}
                                    </SwatchTag>
                                </Group>
                            }
                        >
                            <Text size="xs" c="dimmed">
                                {MAIN_PHASE_LABEL[step.phase as MainPhase] ?? step.phase} · {formatExpected(step)}
                            </Text>
                            {step.derivation && (
                                <Text size="xs" c="dimmed" fs="italic">
                                    {step.derivation}
                                </Text>
                            )}
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
