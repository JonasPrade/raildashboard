import { describe, expect, it } from "vitest";

import { legalStatusLabel } from "./legal";

describe("legalStatusLabel", () => {
    it("names the state of both pages, URL before text", () => {
        expect(
            legalStatusLabel({
                impressum_url: "https://example.org/impressum",
                impressum_markdown: "Text",
                datenschutz_url: "  ",
                datenschutz_markdown: "## Datenschutz",
            }),
        ).toBe("Impressum: Weiterleitung · Datenschutz: eigene Seite");
    });

    it("reports empty pages", () => {
        expect(legalStatusLabel({})).toBe("Impressum: leer · Datenschutz: leer");
    });
});
