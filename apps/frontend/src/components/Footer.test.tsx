import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

vi.mock("../shared/api/queries", () => ({
    useAppSettings: vi.fn(),
}));

import { useAppSettings } from "../shared/api/queries";
import { Footer } from "./Footer";

const mockSettings = useAppSettings as unknown as ReturnType<typeof vi.fn>;

function renderFooter() {
    return render(
        <MemoryRouter>
            <Footer />
        </MemoryRouter>,
    );
}

describe("Footer", () => {
    beforeEach(() => {
        mockSettings.mockReset();
    });

    it("shows the build version and the three links", () => {
        mockSettings.mockReturnValue({ data: undefined });
        renderFooter();

        expect(screen.getByText(`Schienendashboard · Fassung ${__APP_VERSION__}`)).toBeInTheDocument();
        expect(screen.getByRole("link", { name: "Impressum" })).toBeInTheDocument();
        expect(screen.getByRole("link", { name: "Datenschutz" })).toBeInTheDocument();
        expect(screen.getByRole("link", { name: "Dokumentation" })).toHaveAttribute("href", "/documentation");
        expect(screen.getByAltText("Initiative Deutschlandtakt")).toHaveAttribute("src", "/logo-idt-inverse.png");
    });

    it("links the legal pages internally when no URL is set", () => {
        mockSettings.mockReturnValue({
            data: { map_group_mode: "preconfigured", impressum_url: null, datenschutz_url: "  " },
        });
        renderFooter();

        const impressum = screen.getByRole("link", { name: "Impressum" });
        expect(impressum).toHaveAttribute("href", "/impressum");
        expect(impressum).not.toHaveAttribute("target");
        expect(screen.getByRole("link", { name: "Datenschutz" })).toHaveAttribute("href", "/datenschutz");
    });

    it("links the legal pages externally when a URL is set", () => {
        mockSettings.mockReturnValue({
            data: {
                map_group_mode: "preconfigured",
                impressum_url: "https://example.org/impressum",
                datenschutz_url: "https://example.org/datenschutz",
            },
        });
        renderFooter();

        const impressum = screen.getByRole("link", { name: "Impressum" });
        expect(impressum).toHaveAttribute("href", "https://example.org/impressum");
        expect(impressum).toHaveAttribute("target", "_blank");
        expect(impressum).toHaveAttribute("rel", "noopener");
        expect(screen.getByRole("link", { name: "Datenschutz" })).toHaveAttribute(
            "href",
            "https://example.org/datenschutz",
        );
    });
});
