import { describe, expect, it } from "vitest";

import { selectTileUrl } from "./useTileUrl";

const LIGHT = "https://tiles.example/light/{z}/{x}/{y}.png";
const DARK = "https://tiles.example/dark/{z}/{x}/{y}.png";

describe("selectTileUrl", () => {
    it("returns the light URL in the light scheme", () => {
        expect(selectTileUrl("light", LIGHT, DARK)).toBe(LIGHT);
    });

    it("returns the dark URL in the dark scheme when configured", () => {
        expect(selectTileUrl("dark", LIGHT, DARK)).toBe(DARK);
    });

    it("falls back to the light URL when no dark URL is set", () => {
        expect(selectTileUrl("dark", LIGHT, undefined)).toBe(LIGHT);
        expect(selectTileUrl("dark", LIGHT, "")).toBe(LIGHT);
    });

    it("returns undefined without a light URL", () => {
        expect(selectTileUrl("dark", undefined, DARK)).toBeUndefined();
        expect(selectTileUrl("light", "", "")).toBeUndefined();
    });
});
