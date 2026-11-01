import { useMemo, useState } from "react";
import { Anchor, Box, Button, Collapse, Stack, Text } from "@mantine/core";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

import { useIsMobile } from "../../../../shared/hooks/useBreakpoint";
import { useSubprojectsTimeline } from "../../../../shared/api/queries";
import { ErrorState } from "../../../../shared/ui/ErrorState";
import { LoadingState } from "../../../../shared/ui/LoadingState";
import { TimelineAxis, TimelineLegend, TimelineRow } from "../../../timeline/TimelineView";
import { computeRange, sortRows, todayUtc, yearTicks } from "../../../timeline/timelineLayout";

/**
 * Collapsible timeline below the planning state of a superior project: one row
 * per direct subproject on a shared year axis (same rows as the group timeline,
 * each subproject pooling its own subtree). Loads only once opened.
 */
export default function SubprojectsTimeline({ projectId, count }: { projectId: number; count: number }) {
    const [open, setOpen] = useState(false);

    return (
        <Stack gap="xs">
            <Button
                variant="subtle"
                size="xs"
                px={0}
                leftSection={open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                onClick={() => setOpen((o) => !o)}
                aria-expanded={open}
                style={{ alignSelf: "flex-start" }}
            >
                Zeitstrahl der Unterprojekte ({count})
            </Button>
            <Collapse in={open}>{open && <SubprojectsTimelineBody projectId={projectId} />}</Collapse>
        </Stack>
    );
}

function SubprojectsTimelineBody({ projectId }: { projectId: number }) {
    const isMobile = useIsMobile();
    const { data, isLoading, isError, refetch } = useSubprojectsTimeline(projectId, true);
    const today = useMemo(todayUtc, []);

    const rows = useMemo(() => sortRows(data?.items ?? [], "betrieb"), [data]);
    const range = useMemo(() => computeRange(rows, today), [rows, today]);
    const ticks = useMemo(() => yearTicks(range, isMobile ? 4 : 10), [range, isMobile]);

    if (isLoading) return <LoadingState rows={3} label="Zeitstrahl wird geladen …" />;
    if (isError || !data) {
        return (
            <ErrorState title="Zeitstrahl konnte nicht geladen werden" onRetry={() => void refetch()}>
                Bitte versuche es später erneut.
            </ErrorState>
        );
    }

    const withoutDates = data.without_dates;

    return (
        <Stack gap="sm">
            <Text size="xs" c="dimmed">
                Termine aus VIB-PFA, Fulda-Runde, erwarteten Einträgen und den Verfahren — keine BVWP-Schätzungen.
                Sortiert nach Inbetriebnahme.
            </Text>
            {rows.length === 0 ? (
                <Text size="sm" c="dimmed">
                    Noch kein Unterprojekt hat belastbare Termine.
                </Text>
            ) : (
                <>
                    <TimelineLegend
                        showGap={rows.some((row) => row.construction_periods.length > 1)}
                        showPartial={rows.some((row) => row.milestones.some((m) => m.kind === "PART_IBN"))}
                    />
                    <Box>
                        <TimelineAxis ticks={ticks} range={range} />
                        {rows.map((row) => (
                            <TimelineRow key={row.project_id} row={row} range={range} ticks={ticks} today={today} />
                        ))}
                    </Box>
                </>
            )}
            {withoutDates.length > 0 && (
                <Text size="xs" c="dimmed">
                    Ohne belastbare Termine ({withoutDates.length}):{" "}
                    {withoutDates.map((p, idx) => (
                        <span key={p.project_id}>
                            {idx > 0 && ", "}
                            <Anchor component={Link} to={`/projects/${p.project_id}`} size="xs">
                                {p.name}
                            </Anchor>
                        </span>
                    ))}
                </Text>
            )}
        </Stack>
    );
}
