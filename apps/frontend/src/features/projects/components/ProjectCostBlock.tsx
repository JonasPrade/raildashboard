import { Badge, Group, Stack, Tooltip } from "@mantine/core";
import { Stat, StatBand } from "../../../shared/ui/Stat";
import { useProjectFinves, useProjectInfraplan } from "../../../shared/api/queries";
import { formatMio } from "../../infraplan/infraplanFormat";
import { committedFinveMio } from "./projectCost";

// ---------------------------------------------------------------------------
// Cost block on the project page (docs/features/feature-infraplan-import.md →
// „Kosten“): the Infraplan's Gesamtkostenprognose as the headline figure,
// next to it the FinVe funds committed by the federal budget. Deliberately no
// coverage ratio — other bodies co-finance, a ratio would mislead.
// ---------------------------------------------------------------------------

export default function ProjectCostBlock({ projectId }: { projectId: number }) {
    const { data: infraplan } = useProjectInfraplan(projectId);
    const { data: finves } = useProjectFinves(projectId);
    const forecast = infraplan?.cost_forecast ?? null;
    const committed = committedFinveMio(finves ?? []);

    // Only with an Infraplan figure: the FinVe funds alone are already shown
    // in the FinVe section below.
    if (!forecast) return null;

    const footnotes = Object.entries(forecast.footnotes ?? {});

    const forecastValue = (
        <Tooltip
            disabled={footnotes.length === 0}
            label={footnotes.map(([nr, text]) => `${nr}) ${text}`).join("\n")}
            multiline
            w={320}
            withArrow
            style={{ whiteSpace: "pre-line" }}
            events={{ hover: true, focus: true, touch: true }}
        >
            <span tabIndex={footnotes.length > 0 ? 0 : undefined}>
                {formatMio(forecast.total_mio)}
                {footnotes.length > 0 && <sup style={{ marginLeft: 2 }}>{footnotes.map(([nr]) => nr).join(",")}</sup>}
            </span>
        </Tooltip>
    );

    return (
        <Stack gap="xs">
            <StatBand columns={2}>
                <Stat
                    value={forecastValue}
                    unit="Mio. €"
                    title={
                        <Group gap="xs" wrap="wrap">
                            <span>{forecast.label}</span>
                            {forecast.from_subprojects && (
                                <Badge size="sm" variant="outline">Summe der Teilprojekte</Badge>
                            )}
                        </Group>
                    }
                    label={`Laut Infraplan ${forecast.year}${forecast.is_gvfg ? " — Angabe des Landes, nicht plausibilisiert" : ""}`}
                />
                {committed ? (
                    <Stat
                        value={formatMio(committed.total)}
                        unit="Mio. €"
                        title="Vom Bund zugesichert"
                        label={`${committed.count === 1 ? "Eine Finanzierungsvereinbarung" : `${committed.count} Finanzierungsvereinbarungen`} (FinVe, aktuelle Kosten laut Haushalt)`}
                    />
                ) : (
                    <Stat value="–" title="Vom Bund zugesichert" label="Keine projektbezogene FinVe" />
                )}
            </StatBand>
        </Stack>
    );
}
