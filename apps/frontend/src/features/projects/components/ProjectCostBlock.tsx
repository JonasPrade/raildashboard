import { Badge, Group, SimpleGrid, Stack, Text, Tooltip } from "@mantine/core";
import { ChronicleCard } from "../../../components/chronicle";
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

    return (
        <ChronicleCard>
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg">
                <Stack gap={2}>
                    <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                        {forecast.label}
                    </Text>
                    <Group gap="xs" align="baseline" wrap="wrap">
                        <Tooltip
                            disabled={footnotes.length === 0}
                            label={footnotes.map(([nr, text]) => `${nr}) ${text}`).join("\n")}
                            multiline
                            w={320}
                            withArrow
                            style={{ whiteSpace: "pre-line" }}
                            events={{ hover: true, focus: true, touch: true }}
                        >
                            <Text fw={700} size="xl" tabIndex={footnotes.length > 0 ? 0 : undefined}>
                                {formatMio(forecast.total_mio)} Mio. €
                                {footnotes.length > 0 && (
                                    <sup style={{ color: "var(--mantine-color-blue-6)", marginLeft: 2 }}>
                                        {footnotes.map(([nr]) => nr).join(",")}
                                    </sup>
                                )}
                            </Text>
                        </Tooltip>
                        {forecast.from_subprojects && (
                            <Badge size="sm" variant="light" color="gray">Summe der Teilprojekte</Badge>
                        )}
                    </Group>
                    <Text size="xs" c="dimmed">
                        Laut Infraplan {forecast.year}
                        {forecast.is_gvfg ? " — Angabe des Landes, nicht plausibilisiert" : ""}.
                    </Text>
                </Stack>
                <Stack gap={2}>
                    <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Vom Bund zugesichert</Text>
                    {committed ? (
                        <>
                            <Text fw={700} size="xl">{formatMio(committed.total)} Mio. €</Text>
                            <Text size="xs" c="dimmed">
                                {committed.count === 1 ? "Eine Finanzierungsvereinbarung" : `${committed.count} Finanzierungsvereinbarungen`}{" "}
                                (FinVe, aktuelle Kosten laut Haushalt).
                            </Text>
                        </>
                    ) : (
                        <Text size="sm" c="dimmed">Keine projektbezogene FinVe.</Text>
                    )}
                </Stack>
            </SimpleGrid>
        </ChronicleCard>
    );
}
