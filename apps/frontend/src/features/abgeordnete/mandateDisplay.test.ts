import { describe, expect, it } from "vitest";

import { formatShare, formatWeight } from "./mandateDisplay";

describe("formatWeight", () => {
    it("shows kilometres for a line overlap", () => {
        expect(formatWeight(51.2, "line")).toBe("51 km");
    });

    it("keeps one decimal for short stretches, where the difference matters", () => {
        expect(formatWeight(2.85, "line")).toBe("2,9 km");
    });

    it("says where a station project lies instead of claiming zero kilometres", () => {
        expect(formatWeight(0, "point")).toBe("Lage im Wahlkreis");
    });
});

describe("formatShare", () => {
    it("renders a share as a rounded percentage", () => {
        expect(formatShare(0.94)).toBe("94 %");
        expect(formatShare(1)).toBe("100 %");
    });
});
