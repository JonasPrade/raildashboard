import { Alert, Group, Stack, Text, ThemeIcon } from "@mantine/core";
import { TriangleAlert, Clock } from "lucide-react";

import type { ProgressForecast } from "../../../../shared/api/queries";
import { formatMio } from "../../../gvfg/gvfgFormat";

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

/**
 * Forecast extras below the phase stepper: remaining time of the current phase
 * and the GVFG doubt about the commissioning year. The dated next steps
 * themselves are drawn as the "Prognose" row inside the stepper.
 */
export default function ForecastPanel({
    forecast,
}: {
    forecast: ProgressForecast | null | undefined;
}) {
    const remaining = forecast?.has_data ? forecast.remaining_text : null;
    if (!remaining && !forecast?.ibn_doubt) return null;

    return (
        <Stack gap="sm">
            {remaining && (
                <Group gap="xs">
                    <ThemeIcon variant="light" size="sm" color="violet">
                        <Clock size={16} />
                    </ThemeIcon>
                    <Text size="sm" fw={600}>
                        {remaining}
                    </Text>
                </Group>
            )}
            {forecast?.ibn_doubt && <IbnDoubtAlert doubt={forecast.ibn_doubt} />}
        </Stack>
    );
}
