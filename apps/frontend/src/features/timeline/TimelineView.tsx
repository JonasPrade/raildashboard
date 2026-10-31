import { useMemo, useState, type CSSProperties } from "react";
import { Alert, Anchor, Badge, Box, Button, Group, Select, Stack, Text, Tooltip } from "@mantine/core";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight } from "lucide-react";

import { useIsMobile } from "../../shared/hooks/useBreakpoint";
import { useProjectGroupsTimeline, type ProjectTimeline, type TimelineMilestone } from "../../shared/api/queries";
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
    drawnMarkers,
    markerTime,
    milestoneLabel,
    parseTimelineSort,
    percent,
    shortMilestoneDate,
    sortRows,
    yearTicks,
    type Segment,
    type TimelineRange,
} from "./timelineLayout";
import {
    ASSUMED_OUTLINE,
    fuzzyMask,
    gapFill,
    markerStyle,
    openFill,
    phaseColor,
    plannedFill,
    segmentFill,
} from "./timelineStyles";
import { TIMELINE_COLOR } from "../../shared/theme/semanticColors";
import { LoadingState } from "../../shared/ui/LoadingState";
import ProjectHoverCard from "../projects/ProjectHoverCard";

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
const YEAR_MASK = fuzzyMask(true, false, 60);

function Marker({ milestone, range }: { milestone: TimelineMilestone; range: TimelineRange }) {
    const left = percent(markerTime(milestone), range);
    const evidence = milestone.certainty === "EVIDENCE";
    const style: CSSProperties = markerStyle(
        milestone.kind,
        milestone.phase as MainPhase | null,
        evidence,
        milestone.date_precision,
    );
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

// Inline text of a year-only bar („2028“) or an open area („nach 2031 –
// Termin offen“): on a surface pill so it stays legible on the hatch.
const SEGMENT_LABEL_STYLE: CSSProperties = {
    position: "absolute",
    left: 4,
    top: "50%",
    translate: "0 -50%",
    maxWidth: "calc(100% - 22px)",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    fontSize: 10,
    lineHeight: "12px",
    padding: "0 3px",
    color: "var(--text-strong)",
    background: "color-mix(in srgb, var(--surface) 85%, transparent)",
    pointerEvents: "none",
};

function PhaseSegment({ seg, range }: { seg: Segment; range: TimelineRange }) {
    const color = phaseColor(seg.phase);
    const mask = fuzzyMask(Boolean(seg.fuzzyStart), Boolean(seg.fuzzyEnd));
    return (
        <Tooltip label={seg.title} withArrow disabled={!seg.title} multiline maw={320}>
            <Box
                style={{
                    position: "absolute",
                    left: `${percent(seg.start, range)}%`,
                    width: `${percent(seg.end, range) - percent(seg.start, range)}%`,
                    top: 3,
                    bottom: 3,
                    boxSizing: "border-box",
                    background: seg.open ? openFill(color) : segmentFill(seg.phase, seg.planned),
                    ...(mask && { maskImage: mask, WebkitMaskImage: mask }),
                    ...(seg.assumed && { border: ASSUMED_OUTLINE }),
                }}
            >
                {seg.label && (
                    <span
                        style={
                            seg.open
                                ? // Anchored before the arrow, growing to the left: a narrow
                                  // open area at the axis end still shows the full text.
                                  { ...SEGMENT_LABEL_STYLE, left: "auto", right: 14, maxWidth: "none" }
                                : SEGMENT_LABEL_STYLE
                        }
                    >
                        {seg.label}
                    </span>
                )}
                {seg.open && (
                    <ArrowRight
                        size={12}
                        aria-hidden
                        style={{ position: "absolute", right: 0, top: "50%", translate: "0 -50%", color: "var(--text-strong)" }}
                    />
                )}
            </Box>
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
        () => buildSegments(row.milestones, today, row.construction_periods, range.end, row.pending_parts ?? []),
        [row.milestones, row.construction_periods, today, range.end, row.pending_parts],
    );
    const lifecycle = row.lifecycle_status as LifecycleStatus;
    const opening = row.milestones.find((m) => m.kind === "PHASE" && m.phase === "IN_BETRIEB");
    const summary = row.milestones.map(milestoneLabel).join("; ");

    return (
        // Paused/aborted rows: the lifecycle tag plus a muted name, no opacity
        // (text would fall below 4.5:1).
        <Box py={8} style={{ borderBottom: "1px solid var(--border)" }}>
            <Group justify="space-between" gap="xs" wrap="nowrap" mb={6}>
                <Group gap={6} wrap="nowrap" style={{ minWidth: 0 }}>
                    <ProjectHoverCard projectId={row.project_id}>
                        <Anchor
                            component={Link}
                            to={`/projects/${row.project_id}`}
                            size="sm"
                            fw={600}
                            truncate
                            style={lifecycle === "AKTIV" ? undefined : { color: "var(--text-muted)" }}
                        >
                            {row.name}
                        </Anchor>
                    </ProjectHoverCard>
                    {lifecycle !== "AKTIV" && (
                        <Badge size="xs" variant="light" color="gray" style={{ flexShrink: 0 }}>
                            {LIFECYCLE_LABEL[lifecycle]}
                        </Badge>
                    )}
                </Group>
                <Text size="xs" c="dimmed" className="idt-tnum" style={{ flexShrink: 0 }}>
                    {opening ? `IB ${shortMilestoneDate(opening)}` : row.project_number ?? ""}
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
                        <PhaseSegment key={idx} seg={seg} range={range} />
                    ),
                )}
                <Box
                    style={{
                        position: "absolute",
                        left: `${percent(today, range)}%`,
                        top: -6,
                        bottom: -6,
                        width: 3,
                        translate: "-50% 0",
                        background: TODAY_COLOR,
                        boxShadow: "0 0 0 1px var(--surface)",
                        zIndex: 3,
                    }}
                />
                {drawnMarkers(row.milestones).map((m) => (
                    <Marker key={`${m.kind}-${m.phase ?? ""}-${m.date}`} milestone={m} range={range} />
                ))}
            </Box>
        </Box>
    );
}

function Legend({ showGap, showPartial }: { showGap: boolean; showPartial: boolean }) {
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
            {showPartial && (
                <Group gap={6} wrap="nowrap">
                    {swatch("var(--surface)", {
                        width: 10,
                        boxSizing: "border-box",
                        border: `2px solid ${TIMELINE_COLOR.commissioning}`,
                    })}
                    <Text size="xs">Teil-Inbetriebnahme (weitere Abschnitte offen)</Text>
                </Group>
            )}
            <Group gap={6} wrap="nowrap">
                {swatch(plannedFill("var(--text-muted)"), { boxShadow: "inset 0 0 0 1px var(--text-muted)" })}
                <Text size="xs">geplant</Text>
            </Group>
            {/* Date qualification: how sure a date is (feature-project-progress.md). */}
            <Group gap={6} wrap="nowrap">
                {swatch(phaseColor("BAU"), { width: 22, maskImage: YEAR_MASK, WebkitMaskImage: YEAR_MASK })}
                <Text size="xs">nur Jahr bekannt</Text>
            </Group>
            <Group gap={4} wrap="nowrap">
                {swatch(openFill(phaseColor("BAU")), { width: 22 })}
                <ArrowRight size={12} aria-hidden />
                <Text size="xs">nach … – Termin offen</Text>
            </Group>
            <Group gap={6} wrap="nowrap">
                {swatch("transparent", { border: ASSUMED_OUTLINE, boxSizing: "border-box" })}
                <Text size="xs">Annahme</Text>
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
                {swatch(TODAY_COLOR, { width: 3, height: 14 })}
                <Text size="xs">heute</Text>
            </Group>
        </Group>
    );
}

/**
 * Zeitstrahl der gewählten Projektgruppen: eine Zeile je Projekt mit
 * glaubwürdigen Terminen auf einer gemeinsamen Jahresachse. ``visibleProjectIds``
 * ist das Ergebnis von Suche und „Nur Hauptprojekte" der Listenansicht,
 * ``projectCount`` die Zahl der Projekte aller Gruppen (nach „Nur Hauptprojekte“),
 * aus der sich die Projekte ohne Termine ergeben.
 */
export default function TimelineView({
    groupIds,
    projectCount,
    onlySuperior,
    visibleProjectIds,
    searchActive,
}: {
    groupIds: number[];
    projectCount: number;
    onlySuperior: boolean;
    visibleProjectIds: Set<number>;
    searchActive: boolean;
}) {
    const isMobile = useIsMobile();
    const [searchParams, setSearchParams] = useSearchParams();
    const sort = parseTimelineSort(searchParams.get("sort"));
    const [limit, setLimit] = useState(PAGE_SIZE);
    const { items, isLoading, isError } = useProjectGroupsTimeline(groupIds, onlySuperior);
    const today = useMemo(todayUtc, []);

    const rows = useMemo(
        () => sortRows(items.filter((item) => visibleProjectIds.has(item.project_id)), sort),
        [items, visibleProjectIds, sort],
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
    if (isError) {
        return (
            <Alert color="red" variant="light" title="Zeitstrahl konnte nicht geladen werden">
                Bitte versuche es später erneut.
            </Alert>
        );
    }

    const withoutDates = Math.max(0, projectCount - items.length);

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
            <Legend
                showGap={rows.some((row) => row.construction_periods.length > 1)}
                showPartial={rows.some((row) => row.milestones.some((m) => m.kind === "PART_IBN"))}
            />

            {rows.length === 0 ? (
                <Alert color="blue" variant="light" title="Keine Projekte mit Terminen">
                    {searchActive
                        ? "Für diese Suche gibt es keine Projekte mit belastbaren Terminen."
                        : groupIds.length === 1
                          ? "In dieser Projektgruppe hat noch kein Projekt belastbare Termine."
                          : "In den gewählten Projektgruppen hat noch kein Projekt belastbare Termine."}
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
                                    fontVariantNumeric: "tabular-nums",
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
