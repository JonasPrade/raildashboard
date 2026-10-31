import { describe, expect, it } from "vitest";

import type { ProjectTimeline, TimelineMilestone } from "../../shared/api/queries";
import {
    buildSegments as buildSegmentsWithTitles,
    computeRange,
    drawnMarkers,
    formatMonth,
    markerTime,
    shortMilestoneDate,
    milestoneLabel,
    parseTimelineSort,
    percent,
    sortRows,
    toTime,
    yearTicks,
} from "./timelineLayout";

const TODAY = toTime("2026-10-01");

function phase(
    p: TimelineMilestone["phase"],
    date: string,
    certainty: TimelineMilestone["certainty"] = "CONCRETE",
    date_precision: TimelineMilestone["date_precision"] = "EXACT",
): TimelineMilestone {
    return { kind: "PHASE", phase: p, date, source: "VIB-PFA", certainty, date_precision };
}

// Geometry only — the tooltips are checked separately.
const buildSegments = (...args: Parameters<typeof buildSegmentsWithTitles>) =>
    buildSegmentsWithTitles(...args).map((seg) => {
        const rest = { ...seg };
        delete rest.title;
        return rest;
    });

function row(name: string, milestones: TimelineMilestone[]): ProjectTimeline {
    return {
        project_id: name.length,
        name,
        lifecycle_status: "AKTIV",
        milestones,
        construction_periods: [],
        pending_parts: [],
    };
}

describe("buildSegments", () => {
    it("runs each phase until the next one and splits at today", () => {
        const segs = buildSegments(
            [phase("BAU", "2025-01-01"), phase("GENEHMIGUNGSPLANUNG", "2020-01-01"), phase("IN_BETRIEB", "2030-01-01")],
            TODAY,
        );
        expect(segs).toEqual([
            { phase: "GENEHMIGUNGSPLANUNG", start: toTime("2020-01-01"), end: toTime("2025-01-01"), planned: false },
            { phase: "BAU", start: toTime("2025-01-01"), end: TODAY, planned: false },
            { phase: "BAU", start: TODAY, end: toTime("2030-01-01"), planned: true },
        ]);
    });

    it("extends an ongoing past phase to today and leaves a lone future start as a marker", () => {
        expect(buildSegments([phase("BAU", "2024-05-15")], TODAY)).toEqual([
            { phase: "BAU", start: toTime("2024-05-15"), end: TODAY, planned: false },
        ]);
        expect(buildSegments([phase("BAU", "2028-05-15")], TODAY)).toEqual([]);
    });

    it("draws no bar for contradicting dates", () => {
        expect(buildSegments([phase("BAU", "2030-01-01"), phase("IN_BETRIEB", "2029-01-01")], TODAY)).toEqual([]);
    });

    it("splits the BAU bar of separate construction stages and leaves the pause as a gap", () => {
        // HLK 11: stages 01–07/2028 and 01–07/2031, pooled BAU 2028 → IB 2031.
        const segs = buildSegments(
            [phase("BAU", "2028-01-01"), phase("IN_BETRIEB", "2031-07-01")],
            TODAY,
            [
                { start: "2028-01-01", end: "2028-07-01" },
                { start: "2031-01-01", end: "2031-07-01" },
            ],
        );
        expect(segs).toEqual([
            { phase: "BAU", start: toTime("2028-01-01"), end: toTime("2028-07-01"), planned: true },
            { phase: "BAU", start: toTime("2028-07-01"), end: toTime("2031-01-01"), planned: true, gap: true },
            { phase: "BAU", start: toTime("2031-01-01"), end: toTime("2031-07-01"), planned: true },
        ]);
    });

    it("splits a stage at today and keeps the previous phase", () => {
        const segs = buildSegments(
            [phase("GENEHMIGUNGSPLANUNG", "2020-01-01"), phase("BAU", "2025-01-01"), phase("IN_BETRIEB", "2030-01-01")],
            TODAY,
            [
                { start: "2025-01-01", end: "2027-01-01" },
                { start: "2029-01-01", end: "2030-01-01" },
            ],
        );
        expect(segs).toEqual([
            { phase: "GENEHMIGUNGSPLANUNG", start: toTime("2020-01-01"), end: toTime("2025-01-01"), planned: false },
            { phase: "BAU", start: toTime("2025-01-01"), end: TODAY, planned: false },
            { phase: "BAU", start: TODAY, end: toTime("2027-01-01"), planned: true },
            { phase: "BAU", start: toTime("2027-01-01"), end: toTime("2029-01-01"), planned: true, gap: true },
            { phase: "BAU", start: toTime("2029-01-01"), end: toTime("2030-01-01"), planned: true },
        ]);
    });

    it("draws the plain BAU bar when the periods don't split it", () => {
        const milestones = [phase("BAU", "2028-01-01"), phase("IN_BETRIEB", "2031-07-01")];
        const plain = buildSegments(milestones, TODAY);
        expect(buildSegments(milestones, TODAY, [])).toEqual(plain);
        // Only one period inside the BAU span after clipping.
        expect(buildSegments(milestones, TODAY, [
            { start: "2020-01-01", end: "2021-01-01" },
            { start: "2028-01-01", end: "2031-07-01" },
        ])).toEqual(plain);
    });

    it("ignores PFB and parliamentary milestones", () => {
        const pfb: TimelineMilestone = { kind: "PFB", date: "2024-01-01", source: "Manuell", certainty: "CONCRETE", date_precision: "EXACT" };
        expect(buildSegments([pfb], TODAY)).toEqual([]);
    });
});

describe("range and ticks", () => {
    it("covers all milestones and today in whole years", () => {
        const range = computeRange([row("A", [phase("BAU", "2019-06-01"), phase("IN_BETRIEB", "2034-03-01")])], TODAY);
        expect(range).toEqual({ start: Date.UTC(2019, 0, 1), end: Date.UTC(2035, 0, 1) });
        expect(percent(range.start, range)).toBe(0);
        expect(percent(range.end + 1000, range)).toBe(100);
    });

    it("picks a coarser step for long spans", () => {
        const range = { start: Date.UTC(2010, 0, 1), end: Date.UTC(2041, 0, 1) };
        expect(yearTicks(range, 12)).toEqual([2010, 2015, 2020, 2025, 2030, 2035, 2040]);
        expect(yearTicks({ start: Date.UTC(2024, 0, 1), end: Date.UTC(2028, 0, 1) }, 12)).toEqual([
            2024, 2025, 2026, 2027, 2028,
        ]);
    });
});

describe("sortRows", () => {
    const a = row("Alpha", [phase("IN_BETRIEB", "2033-01-01"), phase("BAU", "2027-01-01")]);
    const b = row("Beta", [phase("IN_BETRIEB", "2029-01-01")]);
    const c = row("Gamma", [phase("BAU", "2025-01-01")]);

    it("sorts by opening with undated rows last", () => {
        expect(sortRows([a, c, b], "betrieb").map((r) => r.name)).toEqual(["Beta", "Alpha", "Gamma"]);
    });

    it("sorts by construction start or name", () => {
        expect(sortRows([a, b, c], "bau").map((r) => r.name)).toEqual(["Gamma", "Alpha", "Beta"]);
        expect(sortRows([c, b, a], "name").map((r) => r.name)).toEqual(["Alpha", "Beta", "Gamma"]);
    });

    it("falls back to the default sort for unknown values", () => {
        expect(parseTimelineSort(null)).toBe("betrieb");
        expect(parseTimelineSort("bau")).toBe("bau");
        expect(parseTimelineSort("x")).toBe("betrieb");
    });
});

describe("labels", () => {
    it("formats dates at their precision and describes milestones", () => {
        expect(formatMonth("2026-05-15")).toBe("05/2026");
        expect(milestoneLabel(phase("BAU", "2026-05-15", "CONCRETE", "MONTH"))).toBe("Baubeginn 05/2026 · VIB-PFA");
        expect(milestoneLabel(phase("BAU", "2026-05-15"))).toBe("Baubeginn 15.05.2026 · VIB-PFA");
        expect(milestoneLabel({ ...phase("BAU", "2024-12-31", "EVIDENCE", "YEAR"), source: "VIB" })).toBe(
            "Bau spätestens seit 2024 · VIB",
        );
        expect(
            milestoneLabel({
                kind: "PFB",
                date: "2024-03-15",
                source: "VIB-PFA",
                certainty: "CONCRETE",
                date_precision: "MONTH",
            }),
        ).toBe("Planfeststellung 03/2024 · VIB-PFA");
    });

    it("names the derivation of an assumed date", () => {
        const ibn = {
            ...phase("IN_BETRIEB", "2028-07-01", "CONCRETE", "ASSUMED"),
            source: "Annahme",
            derivation: "Annahme: 6 Monate Bauzeit ab Baubeginn 2028 (Manuell)",
        };
        expect(milestoneLabel(ibn)).toBe(
            "Inbetriebnahme ca. 07/2028 (Annahme) · Annahme · Annahme: 6 Monate Bauzeit ab Baubeginn 2028 (Manuell)",
        );
    });

    it("shortens the header date by precision", () => {
        expect(shortMilestoneDate(phase("IN_BETRIEB", "2030-12-31", "CONCRETE", "YEAR"))).toBe("2030");
        expect(shortMilestoneDate(phase("IN_BETRIEB", "2032-01-01", "CONCRETE", "NOT_BEFORE"))).toBe("nach 2031");
        expect(shortMilestoneDate(phase("IN_BETRIEB", "2028-07-01", "CONCRETE", "ASSUMED"))).toBe("ca. 07/2028");
        expect(shortMilestoneDate(phase("IN_BETRIEB", "2031-07-01"))).toBe("07/2031");
    });
});

describe("uncertain dates (Datumsqualifikation)", () => {
    const RANGE_END = Date.UTC(2034, 0, 1);

    it("draws a year-only start over the year with a soft edge", () => {
        // Hagen – Hamm: Bau 2028, Inbetriebnahme assumed 07/2028.
        const segs = buildSegments(
            [phase("BAU", "2028-01-01", "CONCRETE", "YEAR"), phase("IN_BETRIEB", "2028-07-01", "CONCRETE", "ASSUMED")],
            TODAY,
        );
        expect(segs).toEqual([
            {
                phase: "BAU",
                start: Date.UTC(2028, 0, 1),
                end: toTime("2028-07-01"),
                planned: true,
                fuzzyStart: true,
                label: "2028",
                assumed: true,
            },
        ]);
    });

    it("spans the whole year when a year-only start has no successor", () => {
        // Derived year dates are stored on 31 Dec: the bar still starts on 1 Jan.
        const [seg] = buildSegments([phase("BAU", "2029-12-31", "CONCRETE", "YEAR")], TODAY);
        expect(seg!.start).toBe(Date.UTC(2029, 0, 1));
        expect(seg!.end - seg!.start).toBeGreaterThan(364 * 24 * 3600 * 1000);
    });

    it("draws an open area instead of a bar for a lower bound", () => {
        const segs = buildSegments(
            [
                phase("BAU", "2032-01-01", "CONCRETE", "NOT_BEFORE"),
                phase("IN_BETRIEB", "2032-07-01", "CONCRETE", "NOT_BEFORE"),
            ],
            TODAY,
            [],
            RANGE_END,
        );
        expect(segs).toEqual([
            {
                phase: "BAU",
                start: toTime("2032-01-01"),
                end: RANGE_END,
                planned: true,
                open: true,
                label: "nach 2031 – Termin offen",
            },
        ]);
    });

    it("keeps a known construction start and leaves the end open for a lower-bound opening", () => {
        const segs = buildSegments(
            [phase("BAU", "2027-03-01"), phase("IN_BETRIEB", "2032-01-01", "CONCRETE", "NOT_BEFORE")],
            TODAY,
            [],
            RANGE_END,
        );
        expect(segs).toEqual([
            { phase: "BAU", start: toTime("2027-03-01"), end: toTime("2032-01-01"), planned: true, fuzzyEnd: true },
            {
                phase: "BAU",
                start: toTime("2032-01-01"),
                end: RANGE_END,
                planned: true,
                open: true,
                label: "Inbetriebnahme nach 2031 – Termin offen",
            },
        ]);
    });

    it("uses the free-text label instead of „Termin offen“", () => {
        const [seg] = buildSegments(
            [{ ...phase("BAU", "2032-01-01", "CONCRETE", "NOT_BEFORE"), date_label: "Priorisierung 2027 offen" }],
            TODAY,
            [],
            RANGE_END,
        );
        expect(seg!.label).toBe("nach 2031 – Priorisierung 2027 offen");
    });

    it("puts the derivation into the bar tooltip", () => {
        const [seg] = buildSegmentsWithTitles(
            [
                phase("BAU", "2028-01-01", "CONCRETE", "YEAR"),
                { ...phase("IN_BETRIEB", "2028-07-01", "CONCRETE", "ASSUMED"), derivation: "Annahme: 6 Monate Bauzeit" },
            ],
            TODAY,
        );
        expect(seg!.title).toBe("Bau: 2028 – ca. 07/2028 (Annahme) · Annahme: 6 Monate Bauzeit");
    });

    it("hides markers of lower bounds and centres year-only markers", () => {
        const open = phase("IN_BETRIEB", "2032-07-01", "CONCRETE", "NOT_BEFORE");
        const year = phase("IN_BETRIEB", "2030-12-31", "CONCRETE", "YEAR");
        expect(drawnMarkers([open, year])).toEqual([year]);
        expect(markerTime(year)).toBe(Date.UTC(2030, 6, 1));
    });

    it("does not stretch the axis beyond the year of a lower bound", () => {
        const range = computeRange([row("A", [phase("BAU", "2032-01-01", "CONCRETE", "NOT_BEFORE")])], TODAY);
        expect(range.end).toBe(Date.UTC(2033, 0, 1));
    });

    describe("parent with open parts (#344)", () => {
        const bau = phase("BAU", "2002-08-10");
        const open = {
            ...phase("IN_BETRIEB", "2027-01-01", "CONCRETE", "NOT_BEFORE"),
            source: "Teilabschnitte",
            derivation: "Termin offen: 2 Abschnitte ohne Inbetriebnahme – TM1, Julbach",
        };
        const partial: TimelineMilestone = {
            kind: "PART_IBN",
            phase: null,
            date: "2017-12-15",
            source: "VIB-PFA",
            certainty: "CONCRETE",
            date_precision: "MONTH",
        };
        const pending = [
            { project_id: 1, name: "TM1", phase: "GENEHMIGUNGSPLANUNG" as const },
            { project_id: 2, name: "Julbach", phase: null },
        ];

        it("ends construction at the partial commissioning and leaves the rest open", () => {
            const segs = buildSegments([bau, open, partial], TODAY, [], RANGE_END, pending);
            expect(segs).toEqual([
                { phase: "BAU", start: toTime("2002-08-10"), end: toTime("2017-12-15"), planned: false },
                {
                    phase: "BAU",
                    start: toTime("2017-12-15"),
                    end: RANGE_END,
                    planned: true,
                    open: true,
                    label: "weitere Abschnitte – Termin offen",
                },
            ]);
        });

        it("names the open parts in the tooltip", () => {
            const segs = buildSegmentsWithTitles([bau, open, partial], TODAY, [], RANGE_END, pending);
            expect(segs[1]!.title).toBe(
                "Inbetriebnahme nach 2026 · Termin offen: 2 Abschnitte ohne Inbetriebnahme – TM1, Julbach · " +
                    "Ohne Inbetriebnahme: TM1, Julbach",
            );
        });

        it("keeps construction running while an open part is being built", () => {
            const building = [...pending, { project_id: 3, name: "TM3", phase: "BAU" as const }];
            const segs = buildSegments([bau, open, partial], TODAY, [], RANGE_END, building);
            expect(segs[0]).toMatchObject({ phase: "BAU", start: toTime("2002-08-10"), end: TODAY });
            expect(segs.at(-1)).toMatchObject({ open: true, label: "Inbetriebnahme nach 2026 – Termin offen" });
        });

        it("describes the partial commissioning marker", () => {
            expect(milestoneLabel(partial)).toBe("Teil-Inbetriebnahme 12/2017 · VIB-PFA · weitere Abschnitte offen");
            expect(drawnMarkers([open, partial])).toEqual([partial]);
        });
    });
});
