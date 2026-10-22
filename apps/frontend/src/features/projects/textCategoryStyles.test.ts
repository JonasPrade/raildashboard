import { describe, expect, it } from "vitest";

import type { ProjectText, ProjectTextCategory } from "../../shared/api/queries";
import { TEXT_CATEGORY_STYLES, categoryOf, defaultCategory, textCardStyle } from "./textCategoryStyles";

const info: ProjectTextCategory = { id: 1, name: "Info", style: "info" };
const warning: ProjectTextCategory = { id: 2, name: "Warnung", style: "warning" };

function text(category: ProjectTextCategory | null): ProjectText {
    return {
        id: 1,
        header: "H",
        type: 1,
        created_at: 0,
        updated_at: 0,
        text_type: { id: 1, name: "Kommentar" },
        category_id: category?.id ?? null,
        category,
        is_public: true,
        attachments: [],
    };
}

describe("textCategoryStyles", () => {
    it("colours edge and icon of every style through a token", () => {
        for (const display of Object.values(TEXT_CATEGORY_STYLES)) {
            expect(display.iconColor).toMatch(/^var\(--[a-z0-9-]+\)$/);
            if (display.edge !== null) expect(display.edge).toMatch(/^var\(--[a-z0-9-]+\)$/);
        }
    });

    it("gives every style but neutral an edge (W5)", () => {
        const edged = Object.entries(TEXT_CATEGORY_STYLES)
            .filter(([, d]) => d.edge !== null)
            .map(([style]) => style);
        expect(edged).toEqual(["info", "warning", "critical"]);
        expect(TEXT_CATEGORY_STYLES.info.edge).toBe("var(--idt-cyan)");
        expect(TEXT_CATEGORY_STYLES.warning.edge).toBe("var(--idt-warning)");
    });

    it("keeps icons in ink except for critical", () => {
        const red = Object.entries(TEXT_CATEGORY_STYLES)
            .filter(([, d]) => d.iconColor === "var(--idt-danger)")
            .map(([style]) => style);
        expect(red).toEqual(["critical"]);
        expect(TEXT_CATEGORY_STYLES.info.iconColor).toBe("var(--text-strong)");
    });

    it("draws an 8px left edge without frame or fill", () => {
        expect(textCardStyle("var(--idt-danger)")).toEqual({ borderLeft: "8px solid var(--idt-danger)", paddingLeft: 16 });
        expect(textCardStyle(null).borderLeft).toBe("8px solid transparent");
    });

    it("defaults to Info, else the oldest category", () => {
        expect(defaultCategory([warning, info])).toBe(info);
        expect(defaultCategory([{ ...warning, id: 5 }, { id: 3, name: "Hinweis", style: "neutral" }])?.id).toBe(3);
        expect(defaultCategory([])).toBeNull();
    });

    it("shows texts without a category as the default", () => {
        expect(categoryOf(text(null), [info, warning])).toBe(info);
        expect(categoryOf(text(warning), [info, warning])).toBe(warning);
    });
});
