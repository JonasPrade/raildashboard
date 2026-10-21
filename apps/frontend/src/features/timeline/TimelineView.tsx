import { useMemo, useState, type CSSProperties } from "react";
import { Alert, Anchor, Badge, Box, Button, Group, Select, Stack, Text, Tooltip } from "@mantine/core";
import { Link, useSearchParams } from "react-router-dom";

import { useIsMobile } from "../../shared/hooks/useBreakpoint";
import { useProjectGroupTimeline, type ProjectTimeline, type TimelineMilestone } from "../../shared/api/queries";
import {
    LIFECYCLE_LABEL,
    MAIN_PHASE_LABEL,
    type LifecycleStatus,
    type MainPhase,
} from "../projects/components/progress/phaseMeta";
import {
    TIMELINE_SORT_OPTIONS,
    buildSegments,
    computeRange,
    formatMonth,
    milestoneLabel,
    parseTimelineSort,
    percent,
    sortRows,
    toTime,
    yearTicks,
    type TimelineRange,
} from "./timelineLayout";
import { gapFill, markerStyle, phaseColor, plannedFill, segmentFill } from "./timelineStyles";
import { TIMELINE_COLOR } from "../../shared/theme/semanticColors";
import { LoadingState } from "../../shared/ui/LoadingState";

// Rows rendered per step, like the card list.
const PAGE_SIZE = 60;
const TRACK_HEIGHT = 16;
const LEGEND_PHASES: MainPhase[] = ["VORPLANUNG", "GENEHMIGUNGSPLANUNG", "BAU", "IN_BETRIEB"];

const TODAY_COLOR = TIMELINE_COLOR.today;

function todayUtc(): number {
    const now = new Date();
    return Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
}

// Pause between construction stages: a thin dashed line in seq-4 on the
// neutral track — clearly not construction, but still one project.
const GAP_LABEL = "zwischen Bauetappen";

function Marker({ milestone, range }: { milestone: TimelineMilestone; range: TimelineRange }) {
    const left = percent(toTime(milestone.date), range);
    const evidence = milestone.certainty === "EVIDENCE";
    const style: CSSProperties = markerStyle(milestone.kind, milestone.phase as MainPhase | null, evidence);
    return (
        <Tooltip label={milestoneLabel(milestone)} withArrow>
            <Box
                style={{
                    position: "absolute",
                    left: `${left}%`,
                    top: "50%",
                    translate: "-50% -50%",
                    zIndex: 2,
                    boxSizing: "border-box",
                    ...style,
                }}
            />
        </Tooltip>
    );
}

function TimelineRow({
    row,
    range,
    ticks,
    today,
}: {
    row: ProjectTimeline;
    range: TimelineRange;
    ticks: number[];
    today: number;
}) {
    const segments = useMemo(
        () => buildSegments(row.milestones, today, row.construction_periods),
        [row.milestones, row.construction_periods, today],
    );
    const lifecycle = row.lifecycle_status as LifecycleStatus;
    const opening = row.milestones.find((m) => m.kind === "PHASE" && m.phase === "IN_BETRIEB");
    const summary = row.milestones.map(milestoneLabel).join("; ");

    return (
        <Box py={8} style={{ borderBottom: "1px solid var(--border)", opacity: lifecycle === "AKTIV" ? 1 : 0.55 }}>
            <Group justify="space-between" gap="xs" wrap="nowrap" mb={6}>
                <Group gap={6} wrap="nowrap" style={{ minWidth: 0 }}>
                    <Anchor component={Link} to={`/projects/${row.project_id}`} size="sm" fw={600} truncate>
                        {row.name}
                    </Anchor>
                    {lifecycle !== "AKTIV" && (
                        <Badge size="xs" variant="light" color="gray" style={{ flexShrink: 0 }}>
                            {LIFECYCLE_LABEL[lifecycle]}
                        </Badge>
                    )}
                </Group>
                <Text size="xs" c="dimmed" style={{ flexShrink: 0, fontFamily: "var(--font-mono)" }}>
                    {opening ? `IB ${formatMonth(opening.date)}` : row.project_number ?? ""}
                </Text>
            </Group>
            <Box
                role="img"
                aria-label={`${row.name}: ${summary}`}
                style={{
                    position: "relative",
                    height: TRACK_HEIGHT,
                    background: TIMELINE_COLOR.track,
                }}
            >
                {ticks.map((year) => (
                    <Box
                        key={year}
                        style={{
                            position: "absolute",
                            left: `${percent(Date.UTC(year, 0, 1), range)}%`,
                            top: 0,
                            bottom: 0,
                            width: 1,
                            background: "var(--border)",
                        }}
                    />
                ))}
                {segments.map((seg, idx) =>
                    seg.gap ? (
                        <Tooltip key={idx} label={GAP_LABEL} withArrow>
                            <Box
                                style={{
                                    position: "absolute",
                                    left: `${percent(seg.start, range)}%`,
                                    width: `${percent(seg.end, range) - percent(seg.start, range)}%`,
                                    top: "50%",
                                    height: 2,
                                    translate: "0 -50%",
                                    background: gapFill(),
                                }}
                            />
                        </Tooltip>
                    ) : (
                        <Box
                            key={idx}
                            style={{
                                position: "absolute",
                                left: `${percent(seg.start, range)}%`,
                                width: `${percent(seg.end, range) - percent(seg.start, range)}%`,
                                top: 3,
                                bottom: 3,
                                background: segmentFill(seg.phase, seg.planned),
                            }}
                        />
                    ),
                )}
                <Box
                    style={{
                        position: "absolute",
                        left: `${percent(today, range)}%`,
                        top: -2,
                        bottom: -2,
                        width: 2,
                        translate: "-50% 0",
                        background: TODAY_COLOR,
                        zIndex: 1,
                    }}
                />
                {row.milestones.map((m) => (
                    <Marker key={`${m.kind}-${m.phase ?? ""}-${m.date}`} milestone={m} range={range} />
                ))}
            </Box>
        </Box>
    );
}

function Legend({ showGap }: { showGap: boolean }) {
    const swatch = (background: string, extra?: CSSProperties) => (
        <Box style={{ width: 14, height: 10, background, flexShrink: 0, ...extra }} />
    );
    return (
        <Group gap="md" wrap="wrap">
            {LEGEND_PHASES.map((phase) => (
                <Group key={phase} gap={6} wrap="nowrap">
                    {phase === "IN_BETRIEB"
                        ? swatch(TIMELINE_COLOR.commissioning, { width: 10 })
                        : swatch(phaseColor(phase))}
                    <Text size="xs">{MAIN_PHASE_LABEL[phase]}</Text>
                </Group>
            ))}
            <Group gap={6} wrap="nowrap">
                {swatch(plannedFill("var(--text-muted)"), { boxShadow: "inset 0 0 0 1px var(--text-muted)" })}
                <Text size="xs">geplant</Text>
            </Group>
            {showGap && (
                <Group gap={6} wrap="nowrap">
                    {swatch(gapFill(), { height: 2 })}
                    <Text size="xs">{GAP_LABEL}</Text>
                </Group>
            )}
            <Group gap={6} wrap="nowrap">
                {swatch(TIMELINE_COLOR.marker, { width: 9, height: 9, transform: "rotate(45deg)" })}
                <Text size="xs">Planfeststellung</Text>
            </Group>
            <Group gap={6} wrap="nowrap">
                {swatch("transparent", { width: 9, height: 9, transform: "rotate(45deg)", border: `2px solid ${TIMELINE_COLOR.marker}` })}
                <Text size="xs">Parl. Befassung</Text>
            </Group>
            <Group gap={6} wrap="nowrap">
                {swatch("transparent", { width: 9, height: 9, borderRadius: "50%", border: `2px solid ${TIMELINE_COLOR.marker}` })}
                <Text size="xs">spätestens seit (Beleg)</Text>
            </Group>
            <Group gap={6} wrap="nowrap">
                {swatch(TODAY_COLOR, { width: 2, height: 14 })}
                <Text size="xs">heute</Text>
            </Group>
        </Group>
    );
}

/**
 * Zeitstrahl einer Projektgruppe: eine Zeile je Projekt mit glaubwürdigen
 * Terminen auf einer gemeinsamen Jahresachse. ``visibleProjectIds`` ist das
 * Ergebnis von Suche und „Nur Hauptprojekte" der Listenansicht.
 */
export default function TimelineView({
    groupId,
    onlySuperior,
    visibleProjectIds,
    searchActive,
}: {
    groupId: number;
    onlySuperior: boolean;
    visibleProjectIds: Set<number>;
    searchActive: boolean;
}) {
    const isMobile = useIsMobile();
    const [searchParams, setSearchParams] = useSearchParams();
    const sort = parseTimelineSort(searchParams.get("sort"));
    const [limit, setLimit] = useState(PAGE_SIZE);
    const { data, isLoading, isError } = useProjectGroupTimeline(groupId, onlySuperior);
    const today = useMemo(todayUtc, []);

    const rows = useMemo(
        () => sortRows((data?.items ?? []).filter((item) => visibleProjectIds.has(item.project_id)), sort),
        [data, visibleProjectIds, sort],
    );
    const range = useMemo(() => computeRange(rows, today), [rows, today]);
    const ticks = useMemo(() => yearTicks(range, isMobile ? 4 : 12), [range, isMobile]);

    const handleSortChange = (value: string | null) => {
        setSearchParams(
            (prev) => {
                if (value && value !== "betrieb") prev.set("sort", value);
                else prev.delete("sort");
                return prev;
            },
            { replace: true },
        );
    };

    if (isLoading) {
        return (
            <LoadingState rows={6} />
        );
    }
    if (isError || !data) {
        return (
            <Alert color="red" variant="light" title="Zeitstrahl konnte nicht geladen werden">
                Bitte versuche es später erneut.
            </Alert>
        );
    }

    const withoutDates = data.without_dates_count;

    return (
        <Stack gap="md">
            <Group justify="space-between" align="flex-end" wrap="wrap" gap="sm">
                <Text size="sm" c="dimmed" style={{ maxWidth: 560 }}>
                    {rows.length === 1 ? "1 Projekt" : `${rows.length} Projekte`} mit belastbaren Terminen
                    {withoutDates > 0 && !searchActive
                        ? ` · ${withoutDates} ${withoutDates === 1 ? "Projekt" : "Projekte"} ohne Termine ausgeblendet`
                        : ""}
                    . Gezeigt werden Termine aus VIB-PFA, Fulda-Runde, erwarteten Einträgen und den Verfahren —
                    keine BVWP-Schätzungen.
                </Text>
                <Select
                    label="Sortierung"
                    data={TIMELINE_SORT_OPTIONS}
                    value={sort}
                    onChange={handleSortChange}
                    allowDeselect={false}
                    w={180}
                />
            </Group>
            <Legend showGap={rows.some((row) => row.construction_periods.length > 1)} />

            {rows.length === 0 ? (
                <Alert color="blue" variant="light" title="Keine Projekte mit Terminen">
                    {searchActive
                        ? "Für diese Suche gibt es keine Projekte mit belastbaren Terminen."
                        : "In dieser Projektgruppe hat noch kein Projekt belastbare Termine."}
                </Alert>
            ) : (
                <Box>
                    <Box
                        style={{
                            position: "sticky",
                            top: 60,
                            zIndex: 3,
                            height: 22,
                            background: "var(--surface)",
                            borderBottom: "1px solid var(--border)",
                        }}
                    >
                        {ticks.map((year) => (
                            <Text
                                key={year}
                                size="xs"
                                c="dimmed"
                                style={{
                                    position: "absolute",
                                    left: `${percent(Date.UTC(year, 0, 1), range)}%`,
                                    // Keep the first/last label inside the track.
                                    translate: year === ticks[0] ? "0 0" : year === ticks.at(-1) ? "-100% 0" : "-50% 0",
                                    fontFamily: "var(--font-mono)",
                                    whiteSpace: "nowrap",
                                }}
                            >
                                {year}
                            </Text>
                        ))}
                    </Box>
                    {rows.slice(0, limit).map((row) => (
                        <TimelineRow key={row.project_id} row={row} range={range} ticks={ticks} today={today} />
                    ))}
                    {rows.length > limit && (
                        <Group justify="center" mt="md">
                            <Button variant="default" onClick={() => setLimit((l) => l + PAGE_SIZE)}>
                                Weitere {Math.min(PAGE_SIZE, rows.length - limit)} von {rows.length - limit} Projekten
                                anzeigen
                            </Button>
                        </Group>
                    )}
                </Box>
            )}
        </Stack>
    );
}
