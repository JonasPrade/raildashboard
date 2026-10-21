import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PRIORITY_WEIGHT, displayStatus, hasCheck, todoStatusTextStyle } from "./todoConstants";

describe("todo status display", () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date("2026-10-21T10:00:00"));
    });
    afterEach(() => vi.useRealTimers());

    it("shows unfinished tasks past their due date as overdue", () => {
        expect(displayStatus("OPEN", "2026-10-20")).toBe("OVERDUE");
        expect(displayStatus("IN_PROGRESS", "2026-10-01")).toBe("OVERDUE");
        expect(displayStatus("OPEN", "2026-10-21")).toBe("OPEN");
        expect(displayStatus("DONE", "2026-10-01")).toBe("DONE");
        expect(displayStatus("OPEN", null)).toBe("OPEN");
    });

    it("marks overdue bold with a 3px red underline and nothing else red", () => {
        expect(todoStatusTextStyle("OVERDUE")).toEqual({
            color: "var(--text-strong)",
            fontWeight: 700,
            borderBottom: "3px solid var(--idt-danger)",
            paddingBottom: 1,
        });
        for (const status of ["OPEN", "IN_PROGRESS", "DONE"] as const) {
            expect(todoStatusTextStyle(status).borderBottom).toBeUndefined();
            expect(todoStatusTextStyle(status).color).not.toContain("danger");
        }
    });

    it("draws done muted with a check", () => {
        expect(todoStatusTextStyle("DONE").color).toBe("var(--text-muted)");
        expect(hasCheck("DONE")).toBe(true);
        expect(hasCheck("OPEN")).toBe(false);
    });

    it("shows priority through weight only", () => {
        expect(PRIORITY_WEIGHT.HIGH).toBeGreaterThan(PRIORITY_WEIGHT.MEDIUM);
        expect(PRIORITY_WEIGHT.MEDIUM).toBeGreaterThan(PRIORITY_WEIGHT.LOW);
    });
});
