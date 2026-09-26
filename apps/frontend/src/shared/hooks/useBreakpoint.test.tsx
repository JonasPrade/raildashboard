import { renderHook } from "@testing-library/react";
import { describe, it, expect, afterEach } from "vitest";

import { COMPACT_QUERY, MOBILE_QUERY, useIsCompact, useIsMobile } from "./useBreakpoint";

const originalMatchMedia = window.matchMedia;

/** Report `matches: true` for exactly the queries listed. */
function mockMatchMedia(matching: string[]) {
    Object.defineProperty(window, "matchMedia", {
        writable: true,
        value: (query: string) => ({
            matches: matching.includes(query),
            media: query,
            onchange: null,
            addEventListener: () => {},
            removeEventListener: () => {},
            addListener: () => {},
            removeListener: () => {},
            dispatchEvent: () => false,
        }),
    });
}

afterEach(() => {
    Object.defineProperty(window, "matchMedia", { writable: true, value: originalMatchMedia });
});

describe("useBreakpoint", () => {
    it("reports a phone viewport as mobile and compact", () => {
        mockMatchMedia([MOBILE_QUERY, COMPACT_QUERY]);

        expect(renderHook(() => useIsMobile()).result.current).toBe(true);
        expect(renderHook(() => useIsCompact()).result.current).toBe(true);
    });

    it("reports a small tablet as compact but not mobile", () => {
        mockMatchMedia([COMPACT_QUERY]);

        expect(renderHook(() => useIsMobile()).result.current).toBe(false);
        expect(renderHook(() => useIsCompact()).result.current).toBe(true);
    });

    it("falls back to the desktop layout when nothing matches", () => {
        mockMatchMedia([]);

        expect(renderHook(() => useIsMobile()).result.current).toBe(false);
        expect(renderHook(() => useIsCompact()).result.current).toBe(false);
    });
});
