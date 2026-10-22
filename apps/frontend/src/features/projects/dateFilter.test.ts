import { describe, expect, it } from "vitest";

import {
    EMPTY_DATE_FILTER,
    dateFilterMarks,
    filterProjectsByDate,
    isDateOpen,
    parseDateFilter,
    writeDateFilter,
} from "./dateFilter";

const project = (name: string, start: string | null, precision: string | null, ibDate: string | null = null, ibPrecision: string | null = null) => ({
    name,
    construction_start_date: start,
    construction_start_precision: precision,
    commissioning_date: ibDate,
    commissioning_precision: ibPrecision,
});

const PROJECTS = [
    project("exact-2029", "2029-03-01", "EXACT"),
    project("year-2028", "2028-01-01", "YEAR"),
    project("year-2031", "2031-01-01", "YEAR"),
    project("month-12-2027", "2027-12-01", "MONTH"),
    project("not-before-2029", "2029-01-01", "NOT_BEFORE", "2029-07-01", "NOT_BEFORE"),
    project("assumed-2030", "2030-06-01", "ASSUMED"),
    project("no-date", null, null),
    project("ib-open", "2027-03-01", "EXACT", "2032-01-01", "NOT_BEFORE"),
];

const names = (list: { name: string }[]) => list.map((p) => p.name).sort();

describe("filterProjectsByDate", () => {
    it("Bau 2028–2030 never counts a lower bound", () => {
        const hits = filterProjectsByDate(PROJECTS, { ...EMPTY_DATE_FILTER, bauFrom: 2028, bauTo: 2030 });
        expect(names(hits)).toEqual(["assumed-2030", "exact-2029", "year-2028"]);
    });

    it("open-ended ranges", () => {
        expect(names(filterProjectsByDate(PROJECTS, { ...EMPTY_DATE_FILTER, bauFrom: 2031 }))).toEqual(["year-2031"]);
        expect(names(filterProjectsByDate(PROJECTS, { ...EMPTY_DATE_FILTER, bauTo: 2027 }))).toEqual([
            "ib-open",
            "month-12-2027",
        ]);
    });

    it("„Termin offen“ selects lower bounds of start or opening", () => {
        const hits = filterProjectsByDate(PROJECTS, { ...EMPTY_DATE_FILTER, open: true });
        expect(names(hits)).toEqual(["ib-open", "not-before-2029"]);
        expect(isDateOpen(project("x", "2029-01-01", "EXACT"))).toBe(false);
    });

    it("IB range excludes a lower-bound opening", () => {
        const hits = filterProjectsByDate(PROJECTS, { ...EMPTY_DATE_FILTER, ibFrom: 2029, ibTo: 2035 });
        expect(names(hits)).toEqual([]);
    });

    it("returns the same array without an active filter", () => {
        expect(filterProjectsByDate(PROJECTS, EMPTY_DATE_FILTER)).toBe(PROJECTS);
    });
});

describe("URL and marks", () => {
    it("round-trips through the URL and drops malformed years", () => {
        const params = writeDateFilter(new URLSearchParams("group=3"), {
            ...EMPTY_DATE_FILTER,
            bauFrom: 2028,
            bauTo: 2030,
            open: true,
        });
        expect(params.toString()).toBe("group=3&bau_von=2028&bau_bis=2030&termin_offen=1");
        expect(parseDateFilter(params)).toEqual({ ...EMPTY_DATE_FILTER, bauFrom: 2028, bauTo: 2030, open: true });
        expect(parseDateFilter(new URLSearchParams("bau_von=20x8&ib_bis=2031"))).toEqual({
            ...EMPTY_DATE_FILTER,
            ibTo: 2031,
        });
    });

    it("labels the active parts", () => {
        const marks = dateFilterMarks({ bauFrom: 2028, bauTo: 2030, ibFrom: 2032, ibTo: null, open: true });
        expect(marks.map((m) => m.label)).toEqual(["Bau 2028–2030", "IB ab 2032", "Termin offen"]);
        expect(marks[0]!.without.bauFrom).toBeNull();
    });
});
