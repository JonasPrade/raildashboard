import { Badge, Group, Stack, Tooltip } from "@mantine/core";
import { CircleHelp } from "lucide-react";
import { Stat, StatBand } from "../../../shared/ui/Stat";
import { useProjectFinvesWithSubprojects, useProjectInfraplan } from "../../../shared/api/queries";
import { formatMio } from "../../infraplan/infraplanFormat";
import { committedFinveMio } from "./projectCost";

// ---------------------------------------------------------------------------
// Cost block on the project page (docs/features/feature-infraplan-import.md →
// „Kosten“): the Infraplan's Gesamtkostenprognose as the headline figure,
// next to it the FinVe funds committed by the federal budget — for a parent
// project including the FinVes of all sub-projects, each once. Deliberately no
// coverage ratio — other bodies co-finance, a ratio would mislead.
// ---------------------------------------------------------------------------

export default function ProjectCostBlock({ projectId }: { projectId: number }) {
    const { data: infraplan } = useProjectInfraplan(projectId);
    const { data: finves } = useProjectFinvesWithSubprojects(projectId);
    const forecast = infraplan?.cost_forecast ?? null;
    const committed = committedFinveMio(finves ?? []);

    // Only with an Infraplan figure: the FinVe funds alone are already shown
    // in the FinVe section below.
    if (!forecast) return null;

    const footnotes = Object.entries(forecast.footnotes ?? {});

    // Footnotes of the Infraplan row behind a "?" next to the title, not as a
    // superscript on the figure (which reads as part of the number).
    const footnoteHelp = footnotes.length > 0 && (
        <Tooltip
            label={footnotes.map(([nr, text]) => `${nr}) ${text}`).join("\n")}
            multiline
            w={320}
            withArrow
            style={{ whiteSpace: "pre-line" }}
            events={{ hover: true, focus: true, touch: true }}
        >
            <span
                tabIndex={0}
                aria-label="Fußnoten des Infraplans"
                style={{ display: "inline-flex", cursor: "help", color: "var(--text-muted)" }}
            >
                <CircleHelp size={16} aria-hidden />
            </span>
        </Tooltip>
    );

    return (
        <Stack gap="xs">
            <StatBand columns={2}>
                <Stat
                    value={formatMio(forecast.total_mio)}
                    unit="Mio. €"
                    title={
                        <Group gap="xs" wrap="wrap">
                            <span>{forecast.label}</span>
                            {footnoteHelp}
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
                        label={`${committed.count === 1 ? "Eine Finanzierungsvereinbarung" : `${committed.count} Finanzierungsvereinbarungen`}${committed.fromSubprojects > 0 ? `, davon ${committed.fromSubprojects} aus Teilprojekten` : ""} (FinVe, aktuelle Kosten laut Haushalt)`}
                    />
                ) : (
                    <Stat value="–" title="Vom Bund zugesichert" label="Keine projektbezogene FinVe" />
                )}
            </StatBand>
        </Stack>
    );
}
