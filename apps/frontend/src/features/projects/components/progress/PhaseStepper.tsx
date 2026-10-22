import { Fragment } from "react";
import { Box, Group, Stack, Text, Tooltip } from "@mantine/core";
import { Check, ChevronRight } from "lucide-react";

import {
    MAIN_PHASE_LABEL,
    MAIN_PHASE_SHORT,
    MILESTONE_LABEL,
    PARALLEL_STATE_LABEL,
    UNKNOWN_LABEL,
    type MainPhase,
    type ParallelState,
    mainPhaseIndex,
    visiblePhases,
} from "./phaseMeta";
import { formatDateShort } from "../../../../shared/format";
import { formatExpected, formatQualifiedDate } from "../../../../shared/datePrecision";
import { FORECAST_SOURCE_COLOR, LANE_STATE_COLOR } from "../../../../shared/theme/semanticColors";
import { SwatchTag } from "../../../../shared/ui/SwatchTag";

export type StepperChild = { project_id: number; name: string };

/** Forecast step as delivered by the progress endpoint. */
export type StepperForecastStep = {
    phase: string;
    expected_date?: string | null;
    source: string;
    date_precision?: string | null;
    date_label?: string | null;
    derivation?: string | null;
};

type Props = {
    /** Effective (override-aware) current phase. */
    current: MainPhase;
    /** Superior span (min..max over children); highlights a range instead of one. */
    spanMin?: MainPhase | null;
    spanMax?: MainPhase | null;
    /** Dimmed when the lifecycle overlay (PAUSIERT/ABGEBROCHEN) is active. */
    dimmed?: boolean;
    /** Leaf project with no phase information → nothing active, "Unbekannt". */
    unknown?: boolean;
    /** Suppress the "completed" marking for phases before the span — used
     * for superiors with unknown children, where we cannot claim every child
     * has passed the earlier phases. */
    noCompleted?: boolean;
    /** For superior projects: subprojects grouped by phase, shown on hover. */
    childrenByPhase?: Partial<Record<MainPhase, StepperChild[]>>;
    /** Whether the Planfeststellung gate (PFB) is relevant for this project.
     * When true, a milestone marker is drawn on the Genehmigungsplanung→Bau
     * connector — that boundary is exactly where the Planfeststellungsbeschluss
     * legally gates the start of construction. Only shown when explicitly set. */
    pfRelevant?: boolean;
    /** Resolved Planfeststellung track state, drives the marker colour. */
    pfState?: ParallelState | null;
    /** PFB date (ISO), shown under the marker when present. */
    pfDate?: string | null;
    /** Whether the parl. Befassung gate is relevant; drawn as a milestone on the
     * Vorplanung→Genehmigungsplanung connector. Only shown when explicitly set. */
    parlRelevant?: boolean;
    /** Resolved parl. Befassung track state, drives the marker colour. */
    parlState?: ParallelState | null;
    /** parl. Befassung date (ISO), shown under the marker when present. */
    parlDate?: string | null;
    /** Planning phases left out entirely (skipped by the project's groups). */
    hiddenPhases?: readonly string[] | null;
    /** Forecast steps; those with a known date are drawn in a "Prognose" row
     * under their phase column, the rest is left out. */
    forecastSteps?: readonly StepperForecastStep[] | null;
};

const ACTIVE: string = LANE_STATE_COLOR.active;
const ACTIVE_FILL: string = LANE_STATE_COLOR.activeFill;
const DONE: string = LANE_STATE_COLOR.done;
const DONE_FRAME: string = LANE_STATE_COLOR.doneFrame;
// Open steps, chevrons and open milestones are graphics: --text-muted reaches 3:1
// in both schemes, the hairline token (--idt-line-strong) only 1.8:1.
const IDLE: string = LANE_STATE_COLOR.idleLine;
const SOURCE_COLOR: Record<string, string> = FORECAST_SOURCE_COLOR;
const SOURCE_FALLBACK_COLOR = "var(--idt-line-strong)";

/** Short cell text of a forecast date at its precision; null when no date is known.
 * An assumed date keeps its "ca." here, the "(Annahme)" goes to the tooltip. */
function forecastCellText(step: StepperForecastStep): string | null {
    if (step.date_precision === "ASSUMED" && step.expected_date) {
        return `ca. ${formatQualifiedDate(step.expected_date, "MONTH")}`;
    }
    return formatQualifiedDate(step.expected_date, step.date_precision);
}

/** Forecast cell in the "Prognose" row: qualified date plus its source. */
function ForecastCell({ phase, date, step }: { phase: MainPhase; date: string; step: StepperForecastStep }) {
    const source = step.source;
    return (
        <Tooltip
            label={
                <Stack gap={2}>
                    <Text size="xs">
                        {MILESTONE_LABEL[phase]} {formatExpected(step)} · Quelle: {source}
                    </Text>
                    {step.derivation && (
                        <Text size="xs" fs="italic">
                            {step.derivation}
                        </Text>
                    )}
                </Stack>
            }
            multiline
            maw={320}
            withArrow
            position="bottom"
            events={{ hover: true, focus: true, touch: true }}
        >
            <Stack gap={3} align="center" style={{ flexShrink: 0, cursor: "default" }}>
                <Text size="xs" fw={600} style={{ lineHeight: 1.1, whiteSpace: "nowrap", fontVariantNumeric: "tabular-nums" }}>
                    {date}
                </Text>
                <SwatchTag size="xs" color={SOURCE_COLOR[source] ?? SOURCE_FALLBACK_COLOR}>
                    {source}
                </SwatchTag>
            </Stack>
        </Tooltip>
    );
}

/**
 * Gate milestone marker rendered on a second tier *below* a timeline connector
 * (linked by a short connector), so the main flow stays intact. Ink/filled when
 * abgeschlossen, violet/filled while it läuft, outline when still offen. Used for the
 * Planfeststellungsbeschluss and the parliamentary involvement.
 */
function Milestone({
    label,
    tooltipPrefix,
    state,
    date,
}: {
    label: string;
    tooltipPrefix: string;
    state: ParallelState | null;
    date: string | null;
}) {
    const done = state === "ABGESCHLOSSEN";
    const running = state === "LAEUFT";
    const color = done ? DONE : running ? ACTIVE : IDLE;
    const filled = done || running;
    const formattedDate = date ? formatDateShort(date) : null;
    const stateLabel = PARALLEL_STATE_LABEL[state ?? "OFFEN"];
    return (
        <Tooltip
            label={`${tooltipPrefix}: ${stateLabel}${formattedDate ? ` · ${formattedDate}` : ""}`}
            withArrow
            position="bottom"
            events={{ hover: true, focus: true, touch: true }}
        >
            <Stack gap={3} align="center" style={{ minWidth: 52, cursor: "default" }}>
                {/* short connector linking the marker up to the timeline boundary */}
                <Box style={{ width: 2, height: 6, backgroundColor: color }} />
                <Box
                    style={{
                        width: 14,
                        height: 14,
                        transform: "rotate(45deg)",
                        border: `2px solid ${color}`,
                        backgroundColor: filled ? color : "transparent",
                    }}
                />
                <Text size="xs" ta="center" fw={done ? 700 : 400} c={filled ? undefined : "dimmed"} style={{ lineHeight: 1.1, whiteSpace: "nowrap" }}>
                    <Group gap={2} wrap="nowrap" component="span" justify="center">
                        {label}
                        {done && <Check size={12} strokeWidth={3} aria-label="abgeschlossen" />}
                    </Group>
                </Text>
                {formattedDate && (
                    <Text ta="center" c="dimmed" style={{ fontSize: 10, lineHeight: 1.1, whiteSpace: "nowrap" }}>
                        {formattedDate}
                    </Text>
                )}
            </Stack>
        </Tooltip>
    );
}

export default function PhaseStepper({
    current,
    spanMin,
    spanMax,
    dimmed,
    unknown,
    noCompleted,
    childrenByPhase,
    pfRelevant,
    pfState,
    pfDate,
    parlRelevant,
    parlState,
    parlDate,
    hiddenPhases,
    forecastSteps,
}: Props) {
    const phases = visiblePhases(hiddenPhases);
    const isSpan = spanMin != null && spanMax != null;
    const currentIdx = mainPhaseIndex(current);
    const minIdx = unknown ? -1 : isSpan ? mainPhaseIndex(spanMin as MainPhase) : currentIdx;
    const maxIdx = unknown ? -1 : isSpan ? mainPhaseIndex(spanMax as MainPhase) : currentIdx;
    // Gate milestones sit on connectors leaving a phase: the parliamentary
    // involvement after Vorplanung (→ Genehmigungsplanung), the PFB after
    // Genehmigungsplanung (→ Bau). With hidden phases a gate moves onto the
    // connector that spans its boundary.
    const parlBoundaryIdx = mainPhaseIndex("VORPLANUNG");
    const pfBoundaryIdx = mainPhaseIndex("GENEHMIGUNGSPLANUNG");
    const spansBoundary = (fromIdx: number, toIdx: number, boundaryIdx: number) =>
        fromIdx <= boundaryIdx && boundaryIdx < toIdx;

    // Only forecast steps with a known date get a cell; "Termin offen" is left out.
    const forecastByPhase: Partial<Record<MainPhase, { date: string; step: StepperForecastStep }>> = {};
    for (const step of forecastSteps ?? []) {
        const date = forecastCellText(step);
        if (date && phases.includes(step.phase as MainPhase)) {
            forecastByPhase[step.phase as MainPhase] = { date, step };
        }
    }
    const hasForecast = Object.keys(forecastByPhase).length > 0;

    // Grid: phase columns alternate with connector columns (chevron + gates).
    // Row 1 = phases, row 2 = gate milestones, rows 3–4 = "Prognose" label + cells.
    const columnCount = phases.length * 2 - 1 + (unknown ? 1 : 0);
    const phaseColumn = (pos: number) => pos * 2 + 1;

    return (
        <Box
            style={{
                display: "grid",
                gridTemplateColumns: [
                    ...phases.flatMap((_, pos) => (pos < phases.length - 1 ? ["minmax(78px, max-content)", "auto"] : ["minmax(78px, max-content)"])),
                    ...(unknown ? ["auto"] : []),
                ].join(" "),
                columnGap: 4,
                justifyContent: "start",
                alignItems: "start",
                overflowX: "auto",
                // Paused: phase colours go grey, text keeps its contrast (no opacity).
                filter: dimmed ? "grayscale(1)" : undefined,
            }}
        >
            {phases.map((phase, pos) => {
                const idx = mainPhaseIndex(phase);
                const nextIdx = pos < phases.length - 1 ? mainPhaseIndex(phases[pos + 1]) : null;
                const inSpan = !unknown && idx >= minIdx && idx <= maxIdx;
                const isCurrent = !unknown && (isSpan ? idx === minIdx || idx === maxIdx : idx === currentIdx);
                const isDone = !unknown && !noCompleted && idx < minIdx;

                // Square markers after the prototype's `.step`: running = violet frame
                // on violet-soft, done = ink frame on the surface with an ink check,
                // open = muted frame. Done is never a green fill (Anwendungsebene).
                const isActive = inSpan || isCurrent;
                let frameColor = IDLE;
                let fill = "transparent";
                if (isActive) {
                    frameColor = ACTIVE;
                    fill = ACTIVE_FILL;
                } else if (isDone) {
                    frameColor = DONE_FRAME;
                    fill = "var(--surface)";
                }

                const phaseChildren = childrenByPhase?.[phase] ?? [];
                const tooltipLabel =
                    phaseChildren.length > 0 ? (
                        <Stack gap={2}>
                            <Text size="xs" fw={700}>
                                {MAIN_PHASE_LABEL[phase]} ({phaseChildren.length})
                            </Text>
                            {phaseChildren.slice(0, 12).map((c) => (
                                <Text key={c.project_id} size="xs">
                                    {c.name}
                                </Text>
                            ))}
                            {phaseChildren.length > 12 && (
                                <Text size="xs" c="dimmed">
                                    + {phaseChildren.length - 12} weitere
                                </Text>
                            )}
                        </Stack>
                    ) : (
                        MAIN_PHASE_LABEL[phase]
                    );

                const forecast = forecastByPhase[phase];
                const column = phaseColumn(pos);

                return (
                    <Fragment key={phase}>
                        <Tooltip label={tooltipLabel} multiline withArrow position="top" events={{ hover: true, focus: true, touch: true }}>
                            <Stack gap={4} align="center" style={{ gridRow: 1, gridColumn: column, cursor: "default" }}>
                                <Box
                                    style={{
                                        position: "relative",
                                        width: 28,
                                        height: 28,
                                        borderRadius: 0,
                                        border: `2px solid ${frameColor}`,
                                        backgroundColor: fill,
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                        color: isActive || isDone ? DONE : "var(--text-body)",
                                        fontVariantNumeric: "tabular-nums",
                                        fontSize: 12,
                                        fontWeight: 700,
                                    }}
                                >
                                    {isDone && !isActive ? (
                                        // Done = ink check, no colour (Anwendungsebene → Status).
                                        <Check size={16} strokeWidth={3} aria-label="abgeschlossen" />
                                    ) : (
                                        pos + 1
                                    )}
                                    {phaseChildren.length > 0 && (
                                        <Box
                                            style={{
                                                position: "absolute",
                                                top: -6,
                                                right: -6,
                                                minWidth: 16,
                                                height: 16,
                                                padding: "0 4px",
                                                borderRadius: 0,
                                                backgroundColor: "var(--surface-inverse)",
                                                color: "var(--text-on-inverse)",
                                                fontSize: 10,
                                                lineHeight: "16px",
                                                textAlign: "center",
                                            }}
                                        >
                                            {phaseChildren.length}
                                        </Box>
                                    )}
                                </Box>
                                <Text
                                    size="xs"
                                    ta="center"
                                    fw={isCurrent ? 700 : 400}
                                    c={inSpan || isCurrent ? undefined : "dimmed"}
                                    style={{ lineHeight: 1.1 }}
                                >
                                    {MAIN_PHASE_SHORT[phase]}
                                </Text>
                            </Stack>
                        </Tooltip>
                        {nextIdx !== null && (
                            <>
                                {/* Arrow stays on the main timeline row, vertically centred
                                    with the phase markers (28px band). */}
                                <Box style={{ gridRow: 1, gridColumn: column + 1, height: 28, display: "flex", alignItems: "center" }}>
                                    <ChevronRight
                                        size={16}
                                        style={{ color: !unknown && idx < maxIdx ? ACTIVE : IDLE }}
                                    />
                                </Box>
                                <Stack gap={4} align="center" style={{ gridRow: 2, gridColumn: column + 1 }}>
                                    {spansBoundary(idx, nextIdx, parlBoundaryIdx) && parlRelevant && (
                                        <Milestone
                                            label="Parl."
                                            tooltipPrefix="Parlamentarische Befassung"
                                            state={parlState ?? null}
                                            date={parlDate ?? null}
                                        />
                                    )}
                                    {spansBoundary(idx, nextIdx, pfBoundaryIdx) && pfRelevant && (
                                        <Milestone
                                            label="PFB"
                                            tooltipPrefix="Planfeststellung"
                                            state={pfState ?? null}
                                            date={pfDate ?? null}
                                        />
                                    )}
                                </Stack>
                            </>
                        )}
                        {forecast && (
                            // Zero-width centred box: a long source tag overflows evenly instead
                            // of widening its phase column and pushing the stepper apart.
                            <Box style={{ gridRow: 4, gridColumn: column, justifySelf: "center", width: 0, display: "flex", justifyContent: "center" }}>
                                <ForecastCell phase={phase} date={forecast.date} step={forecast.step} />
                            </Box>
                        )}
                    </Fragment>
                );
            })}
            {unknown && (
                <Text
                    size="sm"
                    c="dimmed"
                    fs="italic"
                    style={{ gridRow: 1, gridColumn: columnCount, alignSelf: "center", paddingLeft: 8 }}
                >
                    {UNKNOWN_LABEL}
                </Text>
            )}
            {hasForecast && (
                <Text
                    component="div"
                    className="idt-eyebrow"
                    style={{
                        gridRow: 3,
                        gridColumn: "1 / -1",
                        marginTop: 10,
                        paddingTop: 6,
                        borderTop: "1px solid var(--idt-line)",
                    }}
                >
                    Prognose
                </Text>
            )}
        </Box>
    );
}
