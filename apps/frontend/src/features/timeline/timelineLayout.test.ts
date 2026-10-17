import { describe, expect, it } from "vitest";

import type { ProjectTimeline, TimelineMilestone } from "../../shared/api/queries";
import {
    buildSegments,
    computeRange,
    formatMonth,
    milestoneLabel,
    parseTimelineSort,
    percent,
    sortRows,
    toTime,
    yearTicks,
} from "./timelineLayout";

const TODAY = toTime("2026-10-01");

function phase(p: TimelineMilestone["phase"], date: string, certainty: TimelineMilestone["certainty"] = "CONCRETE"): TimelineMilestone {
    return { kind: "PHASE", phase: p, date, source: "VIB-PFA", certainty };
}

function row(name: string, milestones: TimelineMilestone[]): ProjectTimeline {
    return { project_id: name.length, name, lifecycle_status: "AKTIV", milestones, construction_periods: [] };
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
        const pfb: TimelineMilestone = { kind: "PFB", date: "2024-01-01", source: "Manuell", certainty: "CONCRETE" };
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
    it("formats month precision and describes milestones", () => {
        expect(formatMonth("2026-05-15")).toBe("05/2026");
        expect(milestoneLabel(phase("BAU", "2026-05-15"))).toBe("Baubeginn 05/2026 · VIB-PFA");
        expect(milestoneLabel({ ...phase("BAU", "2024-12-31", "EVIDENCE"), source: "VIB" })).toBe(
            "Bau spätestens seit 12/2024 · VIB",
        );
        expect(milestoneLabel({ kind: "PFB", date: "2024-03-15", source: "VIB-PFA", certainty: "CONCRETE" })).toBe(
            "Planfeststellung 03/2024 · VIB-PFA",
        );
    });
});
