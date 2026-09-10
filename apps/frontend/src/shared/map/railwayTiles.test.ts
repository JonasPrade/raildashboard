import { describe, expect, it } from "vitest";

import { resolveRailwayTileUrls } from "./railwayTiles";

describe("resolveRailwayTileUrls", () => {
    it("falls back to the OpenRailwayMap subdomains when nothing is configured", () => {
        const urls = resolveRailwayTileUrls(undefined);
        expect(urls).toHaveLength(3);
        expect(urls.every((url) => url.includes("tiles.openrailwaymap.org/standard"))).toBe(true);
    });

    it("uses the configured tile URL", () => {
        expect(resolveRailwayTileUrls("https://tiles.example.org/rail/{z}/{x}/{y}.png")).toEqual([
            "https://tiles.example.org/rail/{z}/{x}/{y}.png",
        ]);
    });

    it("keeps the default when the variable is set but empty (unset Docker build arg)", () => {
        expect(resolveRailwayTileUrls("")).toHaveLength(3);
        expect(resolveRailwayTileUrls("   ")).toHaveLength(3);
    });

    it("disables the overlay on the opt-out value", () => {
        expect(resolveRailwayTileUrls("off")).toEqual([]);
        expect(resolveRailwayTileUrls(" OFF ")).toEqual([]);
    });
});
