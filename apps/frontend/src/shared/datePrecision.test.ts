import { describe, expect, it } from "vitest";

import { formatExpected, formatQualifiedDate, inPeriod, isOpenDate, normalizeSortDate, qualifiedDateText } from "./datePrecision";

describe("formatQualifiedDate", () => {
    it.each([
        ["2026-02-06", "EXACT", "06.02.2026"],
        ["2027-02-01", "MONTH", "02/2027"],
        ["2028-01-01", "YEAR", "2028"],
        ["2032-01-01", "NOT_BEFORE", "nach 2031"],
        ["2032-07-01", "NOT_BEFORE", "frühestens 07/2032"],
        ["2028-07-01", "ASSUMED", "ca. 07/2028 (Annahme)"],
        ["2026-02-06", null, "06.02.2026"],
    ])("%s %s → %s", (iso, precision, expected) => {
        expect(formatQualifiedDate(iso, precision)).toBe(expected);
    });

    it("returns null without a date", () => {
        expect(formatQualifiedDate(null, "YEAR")).toBeNull();
    });
});

describe("qualifiedDateText", () => {
    it("appends the label", () => {
        expect(qualifiedDateText("2032-01-01", "NOT_BEFORE", "Priorisierung 2027 offen")).toBe(
            "nach 2031 – Priorisierung 2027 offen",
        );
        expect(qualifiedDateText(null, "EXACT", "offen")).toBe("offen");
        expect(qualifiedDateText("2028-01-01", "YEAR", "  ")).toBe("2028");
    });
});

describe("normalizeSortDate", () => {
    it("moves coarse dates to the start of their period", () => {
        expect(normalizeSortDate("2027-02-17", "MONTH")).toBe("2027-02-01");
        expect(normalizeSortDate("2028-09-17", "YEAR")).toBe("2028-01-01");
        expect(normalizeSortDate("2032-07-03", "NOT_BEFORE")).toBe("2032-07-03");
    });
});

describe("inPeriod (Bau 2028–2030)", () => {
    const hit = (iso: string, precision: string) => inPeriod(iso, precision, "2028-03-01", "2030-12-31");

    it("counts exact and assumed dates inside the period", () => {
        expect(hit("2029-05-01", "EXACT")).toBe(true);
        expect(hit("2030-06-01", "ASSUMED")).toBe(true);
        expect(hit("2031-01-02", "EXACT")).toBe(false);
    });

    it("counts a year when it overlaps the period", () => {
        expect(hit("2028-01-01", "YEAR")).toBe(true);
        expect(hit("2027-01-01", "YEAR")).toBe(false);
        expect(hit("2028-02-01", "MONTH")).toBe(false);
    });

    it("never counts a lower bound", () => {
        expect(hit("2029-01-01", "NOT_BEFORE")).toBe(false);
        expect(isOpenDate("NOT_BEFORE")).toBe(true);
    });

    it("handles open ends and missing dates", () => {
        expect(inPeriod("2040-01-01", "EXACT", "2028-01-01", null)).toBe(true);
        expect(inPeriod(null, "EXACT", null, null)).toBe(false);
    });
});

describe("formatExpected", () => {
    it("words forecast steps by precision", () => {
        expect(formatExpected({ expected_date: "2028-01-01", date_precision: "YEAR" })).toBe("voraussichtlich 2028");
        expect(formatExpected({ expected_date: "2032-01-01", date_precision: "NOT_BEFORE" })).toBe(
            "Termin offen – nach 2031",
        );
        expect(formatExpected({ expected_date: "2028-07-01", date_precision: "ASSUMED" })).toBe(
            "ca. 07/2028 (Annahme)",
        );
        expect(formatExpected({ expected_date: null })).toBe("Termin offen");
    });
});
