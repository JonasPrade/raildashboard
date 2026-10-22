import { describe, expect, it } from "vitest";
import { CHART_SERIES, CHART_SERIES_OVERFLOW } from "../../../shared/theme/semanticColors";
import { buildLegendItems, seriesColor } from "./FinveBudgetDetails";

describe("series colours", () => {
    it("uses the six chart colours, then the overflow colour", () => {
        expect(seriesColor(0)).toBe(CHART_SERIES[0]);
        expect(seriesColor(5)).toBe(CHART_SERIES[5]);
        expect(seriesColor(6)).toBe(CHART_SERIES_OVERFLOW);
        expect(seriesColor(11)).toBe(CHART_SERIES_OVERFLOW);
    });

    it("groups series beyond six as one legend entry 'weitere'", () => {
        const data = Array.from({ length: 9 }, (_, i) => ({ name: `T${i}`, color: seriesColor(i) }));
        const items = buildLegendItems(data);
        expect(items).toHaveLength(7);
        expect(items.at(-1)).toEqual({ label: "weitere (3)", color: CHART_SERIES_OVERFLOW });
        expect(buildLegendItems(data.slice(0, 6))).toHaveLength(6);
    });
});
