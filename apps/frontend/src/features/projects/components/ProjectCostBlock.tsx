import { Badge, Group, Stack, Tooltip } from "@mantine/core";
import { CircleHelp } from "lucide-react";
import { Stat, StatBand } from "../../../shared/ui/Stat";
import { useProjectFinvesWithSubprojects, useProjectGvfg, useProjectInfraplan } from "../../../shared/api/queries";
import { formatMio } from "../../infraplan/infraplanFormat";
import { committedFinveMio, gvfgAidMio } from "./projectCost";

// ---------------------------------------------------------------------------
// Cost block on the project page (docs/features/feature-infraplan-import.md →
// „Kosten“): the Infraplan's Gesamtkostenprognose as the headline figure,
// next to it the FinVe funds committed by the federal budget — for a parent
// project including the FinVes of all sub-projects, each once. Deliberately no
// coverage ratio — other bodies co-finance, a ratio would mislead.
// GVFG aid from the GVFG-Bundesprogramm stands next to the FinVe funds (in
// their place when there is none); without an Infraplan figure the GVFG total
// cost leads.
// ---------------------------------------------------------------------------

export default function ProjectCostBlock({ projectId }: { projectId: number }) {
    const { data: infraplan } = useProjectInfraplan(projectId);
    const { data: finves } = useProjectFinvesWithSubprojects(projectId);
    const { data: gvfgEntries } = useProjectGvfg(projectId);
    const forecast = infraplan?.cost_forecast ?? null;
    const committed = committedFinveMio(finves ?? []);
    const gvfg = gvfgAidMio(gvfgEntries ?? [], projectId);

    // Only with an Infraplan figure or GVFG aid: the FinVe funds alone are
    // already shown in the FinVe section below.
    if (!forecast && !gvfg) return null;

    const footnotes = Object.entries(forecast?.footnotes ?? {});

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

    const gvfgSource = gvfg
        ? `${gvfg.count === 1 ? "Ein Vorhaben" : `${gvfg.count} Vorhaben`}${gvfg.fromSubprojects ? " aus Teilprojekten" : ""}, jüngste Ausgabe`
        : "";
    const gvfgAid = gvfg && (
        <Stat
            value={formatMio(gvfg.aid)}
            unit="Mio. €"
            title="Bundesförderung (GVFG)"
            label={`Finanzhilfen des Bundes laut GVFG-Bundesprogramm — ${gvfgSource}`}
        />
    );

    return (
        <Stack gap="xs">
            <StatBand columns={committed && gvfgAid ? 3 : 2}>
                {forecast ? (
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
                ) : (
                    <Stat
                        value={formatMio(gvfg?.cost)}
                        unit={gvfg?.cost != null ? "Mio. €" : undefined}
                        title="Gesamtkosten (GVFG)"
                        label={`Laut GVFG-Bundesprogramm — ${gvfgSource}`}
                    />
                )}
                {committed ? (
                    <Stat
                        value={formatMio(committed.total)}
                        unit="Mio. €"
                        title="Vom Bund zugesichert"
                        label={`${committed.count === 1 ? "Eine Finanzierungsvereinbarung" : `${committed.count} Finanzierungsvereinbarungen`}${committed.fromSubprojects > 0 ? `, davon ${committed.fromSubprojects} aus Teilprojekten` : ""} (FinVe, aktuelle Kosten laut Haushalt)`}
                    />
                ) : (
                    !gvfgAid && <Stat value="–" title="Vom Bund zugesichert" label="Keine projektbezogene FinVe" />
                )}
                {gvfgAid}
            </StatBand>
        </Stack>
    );
}
