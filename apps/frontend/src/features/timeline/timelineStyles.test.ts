import { describe, expect, it } from "vitest";

import { gapFill, markerStyle, phaseColor, plannedFill, segmentFill } from "./timelineStyles";

describe("timelineStyles", () => {
    it("hatches the planned part in the phase colour", () => {
        expect(plannedFill("var(--idt-seq-4)")).toBe(
            "repeating-linear-gradient(135deg, var(--idt-seq-4) 0 4px, transparent 4px 8px)",
        );
    });

    it("fills past segments solid and planned ones hatched", () => {
        expect(segmentFill("BAU", false)).toBe("var(--idt-seq-5)");
        expect(segmentFill("BAU", true)).toBe(plannedFill("var(--idt-seq-5)"));
        expect(phaseColor("IN_BETRIEB")).toBe("var(--idt-success)");
    });

    it("dashes the stage pause in seq-4", () => {
        expect(gapFill()).toContain("var(--idt-seq-4) 0 4px");
    });

    it("draws commissioning as a square in success, evidence hollow in ink", () => {
        const ib = markerStyle("PHASE", "IN_BETRIEB", false);
        expect(ib).toMatchObject({ width: 10, height: 10, background: "var(--idt-success)" });
        expect(ib.borderRadius).toBeUndefined();
        const ibEvidence = markerStyle("PHASE", "IN_BETRIEB", true);
        expect(ibEvidence.background).toBe("var(--surface)");
        expect(ibEvidence.border).toBe("2px solid var(--text-strong)");
    });

    it("draws diamonds and hollow points in ink", () => {
        expect(markerStyle("PFB", null, false)).toMatchObject({
            transform: "rotate(45deg)",
            background: "var(--text-strong)",
        });
        expect(markerStyle("PARL", null, false).background).toBe("var(--surface)");
        expect(markerStyle("PHASE", "BAU", true)).toMatchObject({
            borderRadius: "50%",
            background: "var(--surface)",
            border: "2px solid var(--text-strong)",
        });
    });
});
