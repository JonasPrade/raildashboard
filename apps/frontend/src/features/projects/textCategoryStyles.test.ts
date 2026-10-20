import { describe, expect, it } from "vitest";

import type { ProjectText, ProjectTextCategory } from "../../shared/api/queries";
import { TEXT_CATEGORY_STYLES, categoryOf, defaultCategory } from "./textCategoryStyles";

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
    it("colours every style through a semantic token", () => {
        for (const display of Object.values(TEXT_CATEGORY_STYLES)) {
            expect(display.color).toMatch(/^var\(--text-cat-/);
        }
    });

    it("highlights only warning and critical with a border", () => {
        const bordered = Object.entries(TEXT_CATEGORY_STYLES)
            .filter(([, d]) => d.border)
            .map(([style]) => style);
        expect(bordered).toEqual(["warning", "critical"]);
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
