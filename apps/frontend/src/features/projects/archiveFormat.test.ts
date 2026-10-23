import { describe, expect, it } from "vitest";

import { formatArchivedAt } from "./archiveFormat";

describe("formatArchivedAt", () => {
    it("formats an ISO timestamp as a German date", () => {
        expect(formatArchivedAt("2026-10-23T09:15:00")).toBe("23.10.2026");
    });

    it("returns null for missing or invalid values", () => {
        expect(formatArchivedAt(null)).toBeNull();
        expect(formatArchivedAt(undefined)).toBeNull();
        expect(formatArchivedAt("kein Datum")).toBeNull();
    });
});
